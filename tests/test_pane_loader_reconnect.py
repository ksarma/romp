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
import re
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
                         "at load the sheet is up with its 30 s failsafe armed, and the two hold events are listened for beside the socket's (wsdown and wsup each carry a second, fork listener since pass 3: the latch; the shell's link word, `message`, and two more wsdown listeners since iOS item 4: the badge's hold; the shim's park and unpark since the parked-pane fix of 2026-10-02)")
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
        # four wsdown listeners since iOS item 4 (2026-10-02): upstream's, the sheet's held latch, and the badge's hold (a wsdown
        # before upstream's line and one after it); two wsup listeners, upstream's and the sheet's held latch (the badge's wsup
        # listener went with ruling B of round 1, 2026-10-03: the pane's reopen no longer restarts its failsafe); ReconnectBadgeHold below
        self.assertEqual(js.count("addEventListener('romp:wsdown'"), 4); self.assertEqual(js.count("addEventListener('romp:wsup'"), 2)



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
// an interval is a timer too (live() counts it, and the clock re-arms it after each run), so a clear on any repeating clock shows
global.setInterval = (fn, ms) => { const id = nextId++; TIMERS.push({ id, fn, ms, at: NOW + ms, live: true, every: ms }); return id; };
global.clearInterval = global.clearTimeout;
// the placement's watch (rwatch) makes one observer at the paint and disconnects it when the badge is down; MOS keeps each made
// observer's callback and what it observes (regs: one {t, o} per target, a target observed again takes its new options, and
// disconnect() drops them all), so the fit cases can deliver a change to the page as the engine would (deliver(), below): only to
// an observer whose options ask for that kind of record on that node (round 2, tests-3: the fake once ignored them)
const MOS = [];
global.MutationObserver = class { constructor(cb) { this.cb = cb; this.regs = []; MOS.push(this); }
  observe(t, o) { this.regs = this.regs.filter((r) => r.t !== t); this.regs.push({ t, o: o || {} }); }
  disconnect() { this.regs = []; } get on() { return this.regs.length > 0; } };
const cls = (S) => ({ add: (c) => S.add(c), remove: (c) => S.delete(c), contains: (c) => S.has(c),
  toggle: (c, on) => { if (on) S.add(c); else S.delete(c); return !!on; } });
const SHEET = { classList: cls(SHEETCLS) };
const BADGE = { classList: cls(BADGECLS), style: {}, contains: (n) => n === BADGE || KIDS.indexOf(n) >= 0,
  getBoundingClientRect: () => (BADGECLS.has('on') ? BADGE_BOX() : { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }) };
// the painted badge's box as the engine would lay it out: fixed, right 8 px (or its inline right), at its inline top, 134 x 25
let BADGE_W = 134, BADGE_H = 25, VIEW_W = 390;
const BADGE_BOX = () => { const r = VIEW_W - (parseInt(BADGE.style.right, 10) || 8), t = parseInt(BADGE.style.top, 10) || 8; return { left: r - BADGE_W, right: r, top: t, bottom: t + BADGE_H, width: BADGE_W, height: BADGE_H }; };
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
  removeEventListener: (t, f) => { DOCL[t] = (DOCL[t] || []).filter((g) => g !== f); },
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
const run = (to) => { for (;;) { const due = TIMERS.filter((t) => t.live && t.at <= to).sort((a, b) => a.at - b.at || a.id - b.id)[0]; if (!due) break; NOW = due.at; due.live = false; if (due.every) { due.at += due.every; due.live = true; } task(due.fn); } NOW = to; };
const after = (ms) => run(NOW + ms);
const live = (ms) => TIMERS.filter((t) => t.live && (ms === undefined || t.ms === ms)).length;   // live(): every live timer, of any length
// the painted state's changes across tasks, from not painted: each {t, on}; [] means the badge never painted
const runs = () => { const r = []; let prev = false; for (const p of PAINTS) { if (p.on !== prev) { r.push({ t: p.t - 1000000, on: p.on }); prev = p.on; } } return r; };
const out = (o) => console.log(JSON.stringify(Object.assign(o, { textWrites: TEXTW })));
"""


class ReconnectBadgeHold(unittest.TestCase):
    """iOS item 4 (2026-10-02): the reconnect cue's glance is the pane's corner badge, 'reconnecting…', with no count. Latches
    around upstream's badge lines, executed over the script _pane_spin returns. (1) The no-flash hold: a drop's badge paints only
    if no fresh frame has come _RECONN_BADGE_HOLD_MS after the drop that started the hold, the page turning visible or a parked
    pane's tap, whichever is latest (a repeat drop while the hold is pending does not move it), so a healthy return shows nothing
    (the lab measured a 386 ms flash on the phone at 919fde73b); the hold delays the first paint and never clears anything.
    (2) The shell latch: on a page with a shell (it has heard the shell's link word) upstream's 30 s failsafe never runs, so a
    painted badge stays until the pane's first fresh frame (ruling B of round 1, 2026-10-03: before it the failsafe stood down
    while the link word said down and restarted at the link-up word and at the pane's own reopen). A page with no shell hears no
    link word and keeps upstream's failsafe, from the paint. The hold reads the constant from the kernel when it has one and
    1000 ms otherwise, so a run at a head without the hold fails on the behaviour, not on a missing name."""

    HOLD = getattr(km, "_RECONN_BADGE_HOLD_MS", 1000)

    def _run(self, scenario, pre=""):
        """`pre` runs after the harness and BEFORE the loader script (the placement case's header, transcript box and ResizeObserver)."""
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node not installed")
        js = km._pane_spin("content", "live-ask")
        script = js[js.index("<script>") + len("<script>"):js.index("</script>")]
        fx = tempfile.mkdtemp()
        path = os.path.join(fx, "badge.js")
        with open(path, "w") as f:
            f.write(_BADGE_HARNESS + "const RHOLD_T = %d;\n" % self.HOLD + pre + script + "\n" + scenario)
        r = subprocess.run([node, path], capture_output=True, text=True, timeout=30)
        shutil.rmtree(fx, ignore_errors=True)
        self.assertEqual(r.returncode, 0, "the loader script threw: " + r.stderr[:800])
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o["textWrites"], [], "nothing writes the badge's text or children: the glance stays 'reconnecting…', no count, in every state")
        return o

    def test_the_constant_is_one_second_and_the_badge_markup_carries_no_count(self):
        self.assertEqual(self.HOLD, 1000, "the approved 1 s hold (ruling 1, 2026-10-03): healthy lab returns end at 386 ms (phone) and 620 ms (desktop)")
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
after(1); const atHold = painted(); const atHoldTimers = { all: live(), failsafe: live(30000) };
after(5000); fire('romp:wsfresh');
out({ justBefore, atHold, atHoldTimers, afterFresh: painted(), liveEnd: live(), runs: runs() });""")
        self.assertIs(o["justBefore"], False, "1 ms before the hold: nothing painted")
        self.assertIs(o["atHold"], True, "at the hold: painted (S1)")
        self.assertEqual(o["atHoldTimers"], {"all": 1, "failsafe": 1}, "the one timer standing is upstream's 30 s failsafe (a page with no shell): nothing else of any length")
        self.assertIs(o["afterFresh"], False, "the fresh frame clears it (S3)")
        self.assertEqual(o["liveEnd"], 0, "no timer left: the clearing was the event, not a timer")
        self.assertEqual(o["runs"], [{"t": self.HOLD, "on": True}, {"t": self.HOLD + 5000, "on": False}], "one paint, one clear")

    def test_on_a_page_with_a_shell_the_badge_stays_past_30s_through_the_link_up_word_and_the_reopen_until_the_fresh_frame(self):
        # S2 then S3: a return into a down link. Before the latch the badge's 30 s failsafe hid it while romp was still dialing, and
        # the page sat stale with no cue until the link came up (the lab's 45 s hung leg at 919fde73b: hidden at +30.09 s, link at
        # +45 s). Since ruling B of round 1 (2026-10-03) neither the link-up word nor the pane's own reopen arms the failsafe either:
        # the badge is read painted 40 s after each of them, at the deadline a restarted failsafe would have had and past it
        o = self._run(r"""
msg({ romp: 'panes', on: {}, link: 'up' });                           // boot: the shell's link is up
vis('hidden'); fire('romp:wsdown');                                   // the socket dies in the background
msg({ romp: 'panes', on: {}, link: 'down' });                         // the shell's abandon at the return says down
vis('visible');                                                       // the return
const atReturn = painted();
after(RHOLD_T); const s1 = { painted: painted(), timers: live() };
after(45000); const past30 = { painted: painted(), timers: live() };  // 46 s after the return, the link still down
msg({ romp: 'link', link: 'up' });                                    // the shell's socket opens (the link word, the other form)
const atLinkUp = { painted: painted(), timers: live() };
after(40000); const linkUp40 = { painted: painted(), timers: live() };
fire('romp:wsup');                                                    // the pane's own socket opens, and no frame comes yet
const atOpen = { painted: painted(), timers: live() };
after(40000); const open40 = { painted: painted(), timers: live() };
fire('romp:wsfresh');
out({ atReturn, s1, past30, atLinkUp, linkUp40, atOpen, open40, afterFresh: painted(), liveEnd: live(), runs: runs() });""")
        self.assertIs(o["atReturn"], False, "the return holds the badge")
        self.assertEqual(o["s1"], {"painted": True, "timers": 0}, "painted at the hold, with no timer of any length (nothing clears it but the fresh frame)")
        self.assertEqual(o["past30"], {"painted": True, "timers": 0}, "still painted 46 s after the return, still with no timer: romp is still dialing (before the latch the failsafe hid it at 30 s)")
        self.assertEqual(o["atLinkUp"], {"painted": True, "timers": 0}, "the link-up word arms nothing (before ruling B it restarted the 30 s failsafe here)")
        self.assertEqual(o["linkUp40"], {"painted": True, "timers": 0}, "40 s after the link-up word: still painted, so no timer took it down")
        self.assertEqual(o["atOpen"], {"painted": True, "timers": 0}, "the pane's own reopen arms nothing either")
        self.assertEqual(o["open40"], {"painted": True, "timers": 0}, "40 s after the reopen with no fresh frame: still painted")
        self.assertIs(o["afterFresh"], False, "the pane's first fresh frame clears it")
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

    def test_a_repeat_drop_while_painted_on_a_page_with_a_shell_leaves_no_failsafe(self):
        # upstream's wsdown line re-arms the 30 s failsafe on every drop over content; on a page with a shell the listener after it
        # stands it down again, so a pane that drops again keeps its badge past 30 s
        o = self._run(r"""
msg({ romp: 'panes', on: {}, link: 'down' });
fire('romp:wsdown'); after(RHOLD_T);
fire('romp:wsup'); const opened = live(30000);                       // the pane's own socket opens: no failsafe (ruling B)
fire('romp:wsdown'); const redropped = live();                       // and drops again with the link still down
after(45000); const after45timers = live();
out({ opened, redropped, after45: painted(), after45timers });""")
        self.assertEqual(o["opened"], 0, "the reopen arms no failsafe on a page with a shell")
        self.assertEqual(o["redropped"], 0, "the repeat drop leaves no timer of any length (upstream's line armed one in the same dispatch)")
        self.assertEqual(o["after45timers"], 0)
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

    # tests-1 of round 1: the fresh frame ends a PENDING hold too (rpend=false in the fork's wsfresh listener). Without it the next
    # drop, on a visible page after a healthy return, found the stale pending flag, pulled the badge back and armed no hold, so the
    # whole outage showed nothing; and a later switch away and back with no drop re-held a badge nothing had raised
    def test_a_drop_after_a_healthy_return_is_held_and_paints_at_its_own_hold(self):
        o = self._run(r"""
fire('romp:wsdown'); after(400); fire('romp:wsfresh');                // a healthy return: the fresh frame inside the hold
after(5000);
fire('romp:wsdown');                                                  // a second drop, the page visible
const atDrop = { painted: painted(), holds: live(RHOLD_T) };
after(RHOLD_T - 1); const justBefore = painted();
after(1);
out({ atDrop, justBefore, atHold: painted(), runs: runs() });""")
        self.assertEqual(o["atDrop"], {"painted": False, "holds": 1}, "the second drop is held: one hold armed (with a stale pending flag it armed none)")
        self.assertIs(o["justBefore"], False)
        self.assertIs(o["atHold"], True, "and the badge paints at that hold: the outage is cued")
        self.assertEqual(o["runs"], [{"t": 400 + 5000 + self.HOLD, "on": True}])

    def test_after_a_healthy_return_a_switch_away_and_back_with_no_drop_paints_nothing(self):
        o = self._run(r"""
fire('romp:wsdown'); after(400); fire('romp:wsfresh');                // a healthy return
after(5000);
vis('hidden'); after(2000); vis('visible');                           // a quick switch over the live socket: no drop
const atReturn = { painted: painted(), live: live() };
after(RHOLD_T + 500);
out({ atReturn, runs: runs(), liveEnd: live() });""")
        self.assertEqual(o["atReturn"], {"painted": False, "live": 0}, "nothing is held: no drop raised the badge (a stale pending flag re-held it here)")
        self.assertEqual(o["runs"], [], "never painted")
        self.assertEqual(o["liveEnd"], 0)

    # fresh-1 of round 1: turning visible re-holds only a badge that is pending or painted. A quick switch away and back over a
    # standing socket (no drop: the shim's keep path) must hold and paint nothing; an unconditional re-hold painted
    # 'reconnecting…' a second after every such switch, over a healthy page
    def test_a_quick_switch_over_a_standing_socket_paints_nothing(self):
        o = self._run(r"""
vis('hidden'); after(3000); vis('visible');
const atReturn = { painted: painted(), live: live() };
after(RHOLD_T + 500);
out({ atReturn, runs: runs(), liveEnd: live() });""")
        self.assertEqual(o["atReturn"], {"painted": False, "live": 0}, "turning visible with nothing pending or painted arms no hold")
        self.assertEqual(o["runs"], [], "never painted")
        self.assertEqual(o["liveEnd"], 0)

    def test_a_page_with_no_shell_keeps_upstreams_failsafe_from_the_paint(self):
        # standalone: no link word ever arrives, so the failsafe is armed per show (the paint) and hides the badge 30 s on
        o = self._run(r"""
fire('romp:wsdown'); after(RHOLD_T);
const s1 = { painted: painted(), failsafe: live(30000), timers: live() };
after(30000);
out({ s1, after30: painted(), runs: runs() });""")
        self.assertEqual(o["s1"], {"painted": True, "failsafe": 1, "timers": 1}, "painted at the hold with upstream's 30 s failsafe, and no other timer")
        self.assertIs(o["after30"], False, "30 s after the paint the failsafe hides it, as upstream's does")

    def test_on_a_page_with_no_shell_a_repeat_drop_over_the_painted_badge_restarts_upstreams_failsafe(self):
        # round 2, tests-1: a pane page opened on its own (no link word) keeps upstream's failsafe, restarted by a repeat drop as
        # upstream's own wsdown line restarts it, so the guide's "takes the badge down after 30 seconds" counts from the last drop.
        # Read at the paint's deadline (a restart moved it), 1 ms before the repeat drop's, and at it
        o = self._run(r"""
fire('romp:wsdown'); after(RHOLD_T);                                  // painted at the hold, the failsafe due 30 s on
after(10000); fire('romp:wsdown');                                    // a repeat drop 10 s after the paint
const atRepeat = { painted: painted(), failsafe: live(30000), timers: live() };
after(20000); const atPaintDeadline = painted();                      // 30 s after the paint
after(10000 - 1); const justBefore = painted();                       // 1 ms before 30 s after the repeat drop
after(1); const atRepeatDeadline = painted();
out({ atRepeat, atPaintDeadline, justBefore, atRepeatDeadline, runs: runs() });""")
        self.assertEqual(o["atRepeat"], {"painted": True, "failsafe": 1, "timers": 1}, "the repeat drop leaves one failsafe of 30 s, and no other timer")
        self.assertIs(o["atPaintDeadline"], True, "30 s after the paint the badge is still painted: the repeat drop moved the deadline")
        self.assertIs(o["justBefore"], True, "1 ms before 30 s after the repeat drop: painted")
        self.assertIs(o["atRepeatDeadline"], False, "30 s after the repeat drop the failsafe takes it down")
        self.assertEqual(o["runs"], [{"t": self.HOLD, "on": True}, {"t": self.HOLD + 40000, "on": False}])

    def test_on_a_page_with_a_shell_the_panes_own_reopen_under_a_down_link_arms_nothing(self):
        # a dead shell loop: the pane's 25 s link backstop dials on its own. Before ruling B of round 1 (2026-10-03) its reopen
        # restarted the failsafe, so a timer took the badge down 30 s later with no fresh frame; now only the fresh frame clears it
        o = self._run(r"""
msg({ romp: 'panes', on: {}, link: 'down' });
fire('romp:wsdown'); after(RHOLD_T);
after(40000); const waiting = { painted: painted(), timers: live() };
fire('romp:wsup'); const opened = live();
after(30000); const after30 = painted();
fire('romp:wsfresh');
out({ waiting, opened, after30, afterFresh: painted() });""")
        self.assertEqual(o["waiting"], {"painted": True, "timers": 0}, "41 s into a down-link wait: painted, with no timer of any length")
        self.assertEqual(o["opened"], 0, "the pane's own open arms nothing")
        self.assertIs(o["after30"], True, "30 s after the reopen, with no fresh frame, still painted")
        self.assertIs(o["afterFresh"], False)

    def test_on_a_page_with_no_shell_the_panes_reopen_leaves_upstreams_failsafe_where_the_paint_set_it(self):
        # fresh-3 of round 1: upstream's failsafe on a page with no shell runs 30 s from the paint (a repeat drop restarts it, as
        # upstream's own wsdown line does); the pane's reopen is not a show and must not restart it. Read at the deadline the paint
        # set, so a restart shows as a badge still painted there (a count of live timers cannot see one: the restart clears the old
        # timer before it arms the new one)
        o = self._run(r"""
fire('romp:wsdown'); after(RHOLD_T);                                  // painted at the hold, failsafe due 30 s on
after(20000); fire('romp:wsup');                                      // the pane's own socket opens 20 s later, no fresh frame
after(10000 - 1); const justBefore = painted();
after(1); const atDeadline = painted();
out({ justBefore, atDeadline, runs: runs() });""")
        self.assertIs(o["justBefore"], True, "1 ms before the paint's deadline: painted")
        self.assertIs(o["atDeadline"], False, "30 s after the paint the failsafe hides it: the reopen did not restart it")
        self.assertEqual(o["runs"], [{"t": self.HOLD, "on": True}, {"t": self.HOLD + 30000, "on": False}])

    def test_on_a_page_with_a_shell_no_link_word_or_reopen_arms_a_failsafe(self):
        # ruling B of round 1 (2026-10-03), the no-re-arm rule: whatever the shell's words say and however often, and whether the
        # pane's own socket opens, a painted badge on a page with a shell has no timer; it is read painted well past every moment a
        # failsafe could have been armed
        o = self._run(r"""
msg({ romp: 'panes', on: {}, link: 'up' });                           // a pane in the shell, the link up: the pane alone drops
fire('romp:wsdown'); after(RHOLD_T); const atPaint = { painted: painted(), timers: live() };
const seen = [];
for (const m of [{ romp: 'panes', on: {}, link: 'up' }, { romp: 'link', link: 'up' }, { romp: 'panes', on: {}, link: 'down' }, { romp: 'link', link: 'up' }]) {
  msg(m); seen.push(live()); after(10000);
}
fire('romp:wsup'); seen.push(live()); after(10000);
msg({ romp: 'link', link: 'up' }); seen.push(live());
after(40000);
out({ atPaint, seen, after: { painted: painted(), timers: live() } });""")
        self.assertEqual(o["atPaint"], {"painted": True, "timers": 0}, "a pane-only drop under an up link paints with no failsafe (before ruling B the paint armed one)")
        self.assertEqual(o["seen"], [0, 0, 0, 0, 0, 0], "no timer after any link word, repeated or not, or after the reopen")
        self.assertEqual(o["after"], {"painted": True, "timers": 0}, "90 s on, with no fresh frame: still painted")

    def test_the_latch_reads_the_link_field_of_both_shell_words_and_nothing_else(self):
        # the page has a shell once a panes word or a link word carries link 'up' or 'down'; a word of another kind, a panes word
        # with no link field and a null message leave it a page with no shell, whose painted badge keeps upstream's failsafe. The
        # first link word stands a failsafe the paint armed down
        for word in ("{ romp: 'panes', on: {}, link: 'down' }", "{ romp: 'link', link: 'up' }"):
            with self.subTest(word=word):
                o = self._run(r"""
msg({ romp: 'other', link: 'down' }); msg({ romp: 'panes', on: {} }); msg({ romp: 'panes', on: {}, link: 'sideways' }); msg(null);
fire('romp:wsdown'); after(RHOLD_T);
const noWord = live(30000);
msg(%s); const firstWord = { timers: live(), painted: painted() };
after(40000); const later = painted();
out({ noWord, firstWord, later });""" % word)
                self.assertEqual(o, {"noWord": 1, "firstWord": {"timers": 0, "painted": True}, "later": True, "textWrites": []},
                                 "no word, no shell: the paint armed upstream's failsafe; the first link word stands it down and the badge stays")

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

    # The badge's first place (finding of 2026-10-02): 8 px below the top of the pane's content container when that container is
    # the pane's scroll area. The chat, the Outline and the Waiting pane have a header above the list, so the first place covers
    # none of the header's controls (upstream's top:8px hid the phone chat's tag filter and + button, the desktop strip's tag
    # filter and gear, and the phone Outline's tag filter and search); the Feed's list has no header above it, so its first place
    # is upstream's 8 px. That is the first place only: since round 1 the painted badge also moves off controls that stay put when
    # the list scrolls (the clear-place cases below). The served legs measure the real geometry (_badge_clear_of_chrome); these
    # cases run the logic in node.
    _PLACE_PRE = r"""
const ROS = [], OBSERVED = [];
global.ResizeObserver = class { constructor(cb) { ROS.push(cb); } observe(el) { OBSERVED.push(el === CONTENT ? 'content' : el && el.id); } };
let CTOP = 44, COVER = 'scroll';                                      // the transcript's top (the phone header's height) and its overflow-y
CONTENT.getBoundingClientRect = () => ({ top: CTOP, left: 0, right: 390, bottom: 700 });
global.getComputedStyle = (el) => ({ overflowY: el === CONTENT ? COVER : 'visible' });
document.documentElement = { id: 'html' };
const resize = (top) => task(() => { CTOP = top; ROS.forEach((cb) => cb([])); });
// the pane's frame starts being rendered (the phone's Chat tab shown): its style resolves and its container gets a box; `notify`
// says whether the observer's callback runs in that task (the engine's resize event) or not yet
const render = (top, notify) => task(() => { CTOP = top; COVER = 'scroll'; if (notify) ROS.forEach((cb) => cb([])); });
const topOf = () => (BADGE.style.top === undefined ? null : BADGE.style.top);
"""
    # Firefox's frame that is not rendered (finding of 2026-10-02, the served Firefox leg): in an iframe that is display:none, as the
    # phone's chat is while another tab shows, Firefox resolves no computed style, so overflow-y reads '' there, and the container has
    # no box. A phone opened on the Feed tab loads the chat that way, so the loader's load-time read sees ''. Probed on Firefox 153 in a
    # bare page (an iframe display:none since load, then shown, hidden and shown): overflow-y '' and a zero box at load and while
    # hidden again, and the frame's first show delivers the observer's first callback; Chromium and WebKit resolve 'scroll' at load.
    _UNRENDERED = ("let CTOP = 44, COVER = 'scroll';", "let CTOP = 0, COVER = '';")

    def _unrendered_pre(self):
        pre = self._PLACE_PRE.replace(*self._UNRENDERED)
        self.assertNotEqual(pre, self._PLACE_PRE, "the harness's load state was replaced: style unresolved, no box")
        return pre

    def test_the_badge_sits_below_the_panes_header_and_moves_with_it_on_resize_events(self):
        o = self._run(r"""
const atLoad = BADGE.style.top;
resize(90); const pinnedNotes = BADGE.style.top;                      // the pinned notes strip appears above the transcript
resize(0); const offScreen = BADGE.style.top;                         // a pane not rendered (display:none) measures 0
fire('romp:wsdown'); after(RHOLD_T); const painted1 = { painted: painted(), top: BADGE.style.top };
out({ atLoad, pinnedNotes, offScreen, painted1, observed: OBSERVED, observers: ROS.length, timers: live() - (painted() ? 1 : 0) });""", pre=self._PLACE_PRE)
        self.assertEqual(o["observed"], ["content", "html"], "one observer on the scroll area and the page")
        self.assertEqual(o["atLoad"], "52px", "at load: 8 px below the transcript's top, clear of the header")
        self.assertEqual(o["pinnedNotes"], "98px", "a resize event places it again under the new top")
        self.assertEqual(o["offScreen"], "8px", "a pane measuring nothing keeps upstream's 8 px until it is shown (its resize event places it)")
        self.assertEqual(o["painted1"], {"painted": True, "top": "8px"}, "the paint places it from the box it reads then: a pane still measuring nothing, 8 px")
        self.assertEqual(o["timers"], 0, "no timer places it: only the paint's failsafe stands")

    def test_a_content_container_that_is_not_a_scroll_area_keeps_upstreams_corner(self):
        o = self._run(r"""
const atLoad = topOf();
resize(90); const atResize = topOf();
fire('romp:wsdown'); after(RHOLD_T); const atPaint = { painted: painted(), top: topOf() };
out({ atLoad, atResize, atPaint, observers: ROS.length });""", pre=self._PLACE_PRE.replace("COVER = 'scroll'", "COVER = 'visible'"))
        self.assertEqual(o["observers"], 1, "the observer is made whatever the load read: the scroll-area test is made at each placement")
        self.assertIsNone(o["atLoad"], "the inline top is never written: upstream's rule places it (top:8px)")
        self.assertIsNone(o["atResize"], "...nor at a resize event")
        self.assertEqual(o["atPaint"], {"painted": True, "top": None}, "...nor at the paint")

    def test_a_pane_rendered_after_load_places_its_badge_at_the_paint(self):
        # THE FIREFOX LEG'S CASE (finding of 2026-10-02): the chat loaded hidden (the phone opened on the Feed tab), so the load read
        # overflow-y '' and no box. Before this the scroll-area test was made once, there: it failed, no observer was made, and the
        # badge, painted after the Chat tab was shown, sat at upstream's top 8 px over the chat header's session picker, tag filter
        # and + button (the served leg: painted at [252, 8, 130, 25]). Here the tab is shown with no resize event reaching the
        # script before the drop, so only the paint can place it.
        o = self._run(r"""
const atLoad = topOf();
render(45, false);
fire('romp:wsdown'); after(RHOLD_T - 1); const justBefore = { painted: painted(), top: topOf() };
after(1); const atPaint = { painted: painted(), top: topOf() };
out({ atLoad, justBefore, atPaint, timers: live() - (painted() ? 1 : 0) });""", pre=self._unrendered_pre())
        self.assertIsNone(o["atLoad"], "a frame not rendered resolves no style: nothing is written at load")
        self.assertEqual(o["justBefore"], {"painted": False, "top": None}, "the hold places nothing: 1 ms before it, still unpainted and unplaced")
        self.assertEqual(o["atPaint"], {"painted": True, "top": "53px"}, "the paint places it 8 px below the shown transcript's top, clear of the header")
        self.assertEqual(o["timers"], 0, "no timer places it: only the paint's failsafe stands")

    # The paint's own turn (adversarial check of 2026-10-02): a placement moved off the paint to a 0 ms timer still reads 53 px once
    # the clock's walk returns, because the walk runs that timer too, so the case above passed it. This case reads the inline top in
    # the paint's own task, the moment the timer callback that turned the badge on returns: before the walk runs another timer, before
    # any microtask, before any frame. The settled read, after that queued work has run, is asserted first: a deferred placement
    # passes it, so a red on the in-turn read is that read alone.
    _IN_TURN = r"""
const ONS = [], FRAMES = [];
global.requestAnimationFrame = (fn) => { FRAMES.push(fn); return FRAMES.length; };   // a frame callback is queued and runs only at frame()
global.cancelAnimationFrame = () => {};
const frame = () => FRAMES.splice(0).forEach((fn) => fn(NOW));
// every timer callback the script arms is wrapped: one whose run turns the badge on records the inline top the badge has as it returns
{ const st = global.setTimeout; global.setTimeout = (fn, ms) => st(() => { const was = painted(); fn(); if (!was && painted()) ONS.push(topOf()); }, ms); }
"""

    def test_the_paint_writes_the_badges_place_in_its_own_turn(self):
        o = self._run(r"""
(async () => {
render(45, false);                                                    // shown with no resize event before the drop: only the paint can place it
fire('romp:wsdown'); after(RHOLD_T);                                  // the paint, the hold's timer task (the walk also runs any 0 ms timer it queued)
await new Promise((r) => setImmediate(r)); frame();                   // then every microtask, and a frame
out({ inTurn: ONS, settled: { painted: painted(), top: topOf() } });
})();""", pre=self._unrendered_pre() + self._IN_TURN)
        self.assertEqual(o["settled"], {"painted": True, "top": "53px"}, "once the queued work has run, the badge is painted 8 px below the shown transcript's top")
        self.assertEqual(o["inTurn"], ["53px"], "the paint writes the badge's place in its own turn: one timer task turns the badge on, and as it returns the inline "
                         "top is already 53px (a placement deferred to a timer, a frame or a microtask has written nothing yet)")

    def test_a_pane_rendered_after_load_is_placed_by_its_resize_events(self):
        # the same load (style unresolved, no box): the observer is made anyway, so the show's resize event places the badge, and a
        # later one (the pinned notes strip appearing) places it again
        o = self._run(r"""
const atLoad = topOf();
render(45, true); const atShow = topOf();
resize(90); const pinnedNotes = topOf();
out({ atLoad, atShow, pinnedNotes, observed: OBSERVED, observers: ROS.length });""", pre=self._unrendered_pre())
        self.assertEqual(o["observed"], ["content", "html"], "one observer on the container and the page, made although the load read no style")
        self.assertIsNone(o["atLoad"])
        self.assertEqual(o["atShow"], "53px", "the show's resize event places it under the transcript's top")
        self.assertEqual(o["pinnedNotes"], "98px", "a later resize event places it again")

    def test_a_badge_painted_while_its_pane_is_not_rendered_is_placed_when_the_pane_is_shown(self):
        # a drop while the chat is still hidden (another tab showing, the pane not parked): the hold paints the badge where nothing
        # can be read, so it keeps its place; the show's resize event (Firefox's first callback for the frame) places it
        o = self._run(r"""
fire('romp:wsdown'); after(RHOLD_T); const hidden = { painted: painted(), top: topOf() };
render(45, true); const shown = { painted: painted(), top: topOf() };
out({ hidden, shown });""", pre=self._unrendered_pre())
        self.assertEqual(o["hidden"], {"painted": True, "top": None}, "painted while nothing can be read: no place written")
        self.assertEqual(o["shown"], {"painted": True, "top": "53px"}, "the show's resize event places the painted badge")

    # tests-5 of round 1: the clamp. A container whose top is above the viewport's (the pane's document scrolled, a negative top)
    # keeps the badge 8 px below the viewport's top, never above it: at a resize event, and at the paint from the box it reads then
    def test_a_container_above_the_viewport_top_keeps_the_badge_8px_below_the_top(self):
        o = self._run(r"""
resize(-30);
out({ atResize: topOf() });""", pre=self._PLACE_PRE)
        self.assertEqual(o["atResize"], "8px", "a resize event with the container's top at -30 px: 8 px, not -22 px")
        o = self._run(r"""
const atLoad = topOf();
render(-30, false);                                                   // the box moves with no resize event before the drop
fire('romp:wsdown'); after(RHOLD_T);
out({ atLoad, atPaint: { painted: painted(), top: topOf() } });""", pre=self._PLACE_PRE)
        self.assertEqual(o["atLoad"], "52px")
        self.assertEqual(o["atPaint"], {"painted": True, "top": "8px"}, "the paint reads the -30 px top and clamps it: 8 px")

    # The clear place (round 1, 2026-10-03: regression-1, extra5-1, correctness-1, correctness-2). The first place alone covered
    # controls that stay put when the content scrolls: the subagent viewer's sticky header and its pin, the chat's landing notice,
    # the Feed's sticky column heads and their drag chips. While painted the badge moves to the nearest place that covers none:
    # a control outside the list, or a control that is or sits in a sticky or fixed element in the list (rfit, robs). Since round 2
    # (2026-10-03) the controls count, not the sticky boxes that hold them (open call 2), and each counts by the part of it that
    # its overflow ancestors leave in view (correctness-1). These cases run the search over a page of fake elements: each has a
    # box, a computed style (its position, cursor, overflow, containment, transform, filter, perspective and will-change), a parent,
    # a padding box (clientLeft, clientTop, clientWidth, clientHeight: its whole box, no border or scrollbar, unless its case sets them,
    # as the padding-box cases of round 3 do) and answers matches() for the one selector entry it carries (so the product's RCTL list
    # must name it) or its cursor. The served legs measure real engines.
    _FIT_PRE = r"""
document.documentElement = { id: 'html', clientWidth: 390, clientHeight: 844 };
const ALL = [CONTENT];                                                // the body's elements in document order
document.body = { getElementsByTagName: (t) => (t === '*' ? ALL : []) };
let STYLE_READS = 0;
global.getComputedStyle = (el) => { STYLE_READS++; return el === CONTENT ? { overflowY: COVER, overflowX: COVER === 'visible' ? 'visible' : 'auto', position: 'static', cursor: document.body.cs.cursor, visibility: 'visible', display: 'block' } : el.cs; };
// the body's computed style: its cursor is 'auto' until a case puts the class of a handle's drag on it (bodyCursor, below); the list
// sets no cursor of its own, so its computed cursor is the body's
document.body.cs = { position: 'static', cursor: 'auto', visibility: 'visible', display: 'block', overflowX: 'visible', overflowY: 'visible', contain: 'none',
  transform: 'none', filter: 'none', perspective: 'none', willChange: 'auto' };
// the list's padding box is its whole box (no border; a scrollbar is not drawn in these cases)
// the list and the body-level elements are the body's children, in document order (the badge apart: the page's last element)
Object.defineProperty(document.body, 'firstElementChild', { get: () => ALL.find((x) => x === CONTENT || !x.parent) || null });
Object.defineProperties(CONTENT, { parentElement: { get: () => document.body }, firstElementChild: { get: () => ALL.find((x) => x.parent === CONTENT) || null },
  nextElementSibling: { get: () => { const sib = ALL.filter((x) => x === CONTENT || !x.parent); return sib[sib.indexOf(CONTENT) + 1] || null; } } });
Object.defineProperties(CONTENT, { clientLeft: { get: () => 0 }, clientTop: { get: () => 0 }, clientWidth: { get: () => { const r = CONTENT.getBoundingClientRect(); return r.right - r.left; } },
  clientHeight: { get: () => { const r = CONTENT.getBoundingClientRect(); return r.bottom - r.top; } } });
const inside = (anc, n) => { for (let e = n; e; e = e.parent) if (e === anc) return true; return false; };
CONTENT.contains = (n) => inside(CONTENT, n);
// each element's attributes, by name (the class, style and hidden values the watch's records name); null when it has none
const attrOf = (t, n) => (t.attrs && Object.prototype.hasOwnProperty.call(t.attrs, n) ? t.attrs[n] : null);
CONTENT.attrs = {}; CONTENT.getAttribute = (n) => attrOf(CONTENT, n); document.body.attrs = {}; document.body.getAttribute = (n) => attrOf(document.body, n);
// add(parent, box [left, top, width, height], { position, cursor, sel, overflow, overflowX, overflowY, contain, transform, filter,
// perspective, willChange, display, clientLeft, clientTop, clientWidth, clientHeight }): an element under `parent` (null: the body,
// outside the list); `overflow` sets both axes; the four client values set its padding box (by default its whole box: 0, 0, its
// width, its height), as a border or a scrollbar would
const add = (parent, box, o) => { o = o || {}; const e = { nodeType: 1, parent, box: box.slice(), sel: o.sel || '', own: o.cursor || null,
  cs: { position: o.position || 'static', cursor: o.cursor || 'auto', visibility: 'visible', display: o.display || 'block',
        overflowX: o.overflowX || o.overflow || 'visible', overflowY: o.overflowY || o.overflow || 'visible', contain: o.contain || 'none',
        transform: o.transform || 'none', filter: o.filter || 'none', perspective: o.perspective || 'none', willChange: o.willChange || 'auto' },
  get parentElement() { return this.parent || document.body; },
  get firstElementChild() { return ALL.find((x) => x.parent === this) || null; },
  get nextElementSibling() { const sib = this.parent ? ALL.filter((x) => x.parent === this.parent) : ALL.filter((x) => x === CONTENT || !x.parent); return sib[sib.indexOf(this) + 1] || null; },
  get clientLeft() { return o.clientLeft || 0; }, get clientTop() { return o.clientTop || 0; },
  get clientWidth() { return o.clientWidth === undefined ? this.box[2] : o.clientWidth; }, get clientHeight() { return o.clientHeight === undefined ? this.box[3] : o.clientHeight; },
  getBoundingClientRect() { const [l, t, w, h] = this.box; return { left: l, top: t, right: l + w, bottom: t + h, width: w, height: h }; },
  contains(n) { return inside(this, n); }, matches(list) { return !!this.sel && list.split(',').indexOf(this.sel) >= 0; },
  attrs: {}, getAttribute(n) { return attrOf(this, n); },
  getElementsByTagName(t) { return t === '*' ? ALL.filter((x) => x !== this && inside(this, x)) : []; } };
  const at = parent ? ALL.lastIndexOf(ALL.filter((x) => inside(parent, x)).pop()) + 1 : ALL.length; ALL.splice(at, 0, e); return e; };
// each element's cursor is the one its case set (`cursor`), else 'auto'. bodyCursor(k) models CSS's inheritance from the body: it
// sets the body's cursor to k (the class of a handle's drag, body.composer-resizing or body.tabbar-resizing, sets ns-resize) and
// gives every element the cursor CSS computes for it, its own where its case set one, else its parent's (the body's for the body's
// own children and the list's), in document order, so a parent is computed before its children
const bodyCursor = (k) => { document.body.cs.cursor = k; for (const e of ALL) if (e !== CONTENT) e.cs.cursor = e.own || (e.parent && e.parent !== CONTENT ? e.parent.cs.cursor : k); };
const rightOf = () => (BADGE.style.right ? BADGE.style.right : '8px');
const at = () => ({ top: topOf(), right: rightOf(), painted: painted() });
// the badge's watch: an observer that asks for attributes (the sheet's own observer watches the list's children alone)
const watchers = () => MOS.filter((m) => m.on && m.regs.some((r) => r.o.attributes));
const mo = () => watchers().length;
// a record reaches an observer that observes its target, or an ancestor of it with subtree, with the options its kind needs: childList,
// or attributes with the attribute in attributeFilter when there is one (the body is every element's ancestor here)
const sees = (r, rec) => (r.t === rec.target || (r.o.subtree && (r.t === document.body || inside(r.t, rec.target)))) &&
  (rec.type === 'childList' ? !!r.o.childList : !!r.o.attributes && (!r.o.attributeFilter || r.o.attributeFilter.indexOf(rec.attributeName) >= 0));
// deliverAll hands each observer, in one callback, the records it sees, in order. An attribute record carries the value the attribute
// had (oldValue) only for an observer whose options ask for it (attributeOldValue); any other gets null there, as the engine gives it
const deliverAll = (recs) => task(() => MOS.forEach((m) => { const mine = recs.filter((rec) => m.regs.some((r) => sees(r, rec)))
  .map((rec) => (m.regs.some((r) => sees(r, rec) && r.o.attributeOldValue) ? rec : Object.assign({}, rec, { oldValue: null }))); if (mine.length) m.cb(mine); }));
const deliver = (rec) => deliverAll([rec]);
const ELEM = { nodeType: 1 }, TEXT = { nodeType: 3 };
// a childList record as the engine gives it: attributeName and oldValue are null on it, as on every record that is not an attribute
// one (round 3, tests-1: the harness left both undefined, which getAttribute(undefined) never equals, so a skip that dropped its type
// check stayed green here while an engine, where both are null and getAttribute(null) is null, would skip every childList record)
const kids = (target, addedNodes, removedNodes) => ({ type: 'childList', target, attributeName: null, oldValue: null, addedNodes, removedNodes });
const change = (target) => deliver(kids(target, [ELEM], []));                                                    // an element added inside `target`
const added = (el) => deliver(kids(el.parent || document.body, [el], []));                                       // `el` added to its parent
const text = (target) => deliver(kids(target, [TEXT], [TEXT]));                                                  // `target`'s text written (textContent)
// an attribute written to a new value (`value`, by default one it never had; null removes it): the record carries the value it had
let WRITES = 0;
const attrRec = (target, name, value) => { name = name || 'style'; const old = attrOf(target, name), v = value === undefined ? (old || '') + ' w' + (++WRITES) : value;
  if (v === null) delete target.attrs[name]; else target.attrs[name] = v;
  return { type: 'attributes', target, attributeName: name, oldValue: old, addedNodes: [], removedNodes: [] }; };
// an attribute written to the value it already has (a setAttribute of that value, a classList.add of a class it holds): the engine
// still queues a record, and its old value is the value the attribute has now
const sameRec = (target, name) => ({ type: 'attributes', target, attributeName: name || 'style', oldValue: attrOf(target, name || 'style'), addedNodes: [], removedNodes: [] });
const attr = (target, name, value) => deliver(attrRec(target, name, value));
const same = (target, name) => deliver(sameRec(target, name));
// the frame clock: the watch asks for a placement at the next animation frame; frame() runs the frames asked for so far
const FRAMES = [];
global.requestAnimationFrame = (fn) => { FRAMES.push(fn); return FRAMES.length; };
global.cancelAnimationFrame = (id) => { if (FRAMES[id - 1]) FRAMES[id - 1] = null; };
const frame = () => task(() => { const fs = FRAMES.splice(0); fs.forEach((fn) => fn && fn(NOW)); });
const scroll = () => task(() => (DOCL.scroll || []).slice().forEach((f) => f({ type: 'scroll' })));
const transition = () => task(() => (DOCL.transitionend || []).slice().forEach((f) => f({ type: 'transitionend' })));   // a CSS transition ended somewhere in the page
// a short view and a short list (a landscape phone with the keyboard up): the page's height and the list's bottom
const shortList = (viewH, bottom) => { document.documentElement.clientHeight = viewH; CONTENT.getBoundingClientRect = () => ({ top: CTOP, left: 0, right: 390, bottom }); };
"""

    def _fit(self, scenario):
        return self._run(scenario, pre=self._PLACE_PRE + self._FIT_PRE)

    def test_a_painted_badge_moves_off_a_control_in_a_sticky_header_in_the_list_and_may_sit_over_its_text(self):
        # the subagent viewer: a sticky line at the list's top (#sub-head, 8 px down) with its pin, a role=button, at the right end.
        # Round 2 (open call 2, 2026-10-03): the pin counts, not the header's box, so the badge stays on the header's line, left of
        # the pin and over the header's text; round 1 sent it below the whole header (91 px)
        o = self._fit(r"""
const head = add(CONTENT, [0, 52, 390, 31], { position: 'sticky' });
add(head, [360, 58, 20, 20], { sel: '[role=button]' });
const atLoad = at();
fire('romp:wsdown'); after(RHOLD_T); const atPaint = at();
out({ atLoad, atPaint, watching: mo() });""")
        self.assertEqual(o["atLoad"], {"top": "52px", "right": "8px", "painted": False}, "unpainted, the first place: no search on a healthy page")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "38px", "painted": True},
                         "painted left of the pin (390 - 360 + 8), over the header's text: 30 px left is a shorter move than 34 px down (58 + 20 + 8)")
        self.assertEqual(o["watching"], 1, "and watching the page for what could move it")

    def test_a_control_drawn_over_the_list_from_outside_it_moves_the_badge_below_it_when_it_appears(self):
        # the landing notice: outside the list, drawn over its top, a pointer cursor and nothing else, shown after the paint
        o = self._fit(r"""
fire('romp:wsdown'); after(RHOLD_T); const atPaint = at();
const notice = add(null, [42, 54, 307, 29], { cursor: 'pointer' });
change(BADGE); frame(); const ownChange = at();                        // a change to the badge alone (its own place written) moves nothing
added(notice); const beforeFrame = at(); frame(); const shown = at();   // the notice added to the page: placed at the next frame
out({ atPaint, ownChange, beforeFrame, shown });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True})
        self.assertEqual(o["ownChange"], {"top": "52px", "right": "8px", "painted": True}, "the badge's own mutations are not a change to the page")
        self.assertEqual(o["beforeFrame"], {"top": "52px", "right": "8px", "painted": True}, "the change asks for a placement at the next frame, not in its own task")
        self.assertEqual(o["shown"], {"top": "91px", "right": "8px", "painted": True}, "the notice shown under it moves it below the notice (54 + 29 + 8)")

    def test_a_narrow_control_at_the_right_edge_moves_the_badge_left_of_it(self):
        # a scroll mark: an 8 x 2 link (data-act) at the list's right edge, outside the list; left is the shorter move
        o = self._fit(r"""
add(null, [381, 60, 8, 2], { sel: '[data-act]' });
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "17px", "painted": True}, "9 px left (390 - 381 + 8), not 18 px down")

    def test_the_feed_column_heads_send_the_badge_below_their_row(self):
        # the desktop Feed: no header above the list (its top is the page's), three sticky column heads at its top, each with a drag
        # chip that has a grab cursor and nothing else; the badge's first place (8 px) is on the second and third heads, and on the
        # third head's chip
        o = self._fit(r"""
resize(0);
for (const [l, w] of [[12, 120], [140, 120], [268, 110]]) { const h = add(CONTENT, [l, 12, w, 29], { position: 'sticky' }); add(h, [l + 2, 14, 68, 20], { cursor: 'grab' }); }
const atLoad = at();
fire('romp:wsdown'); after(RHOLD_T);
out({ atLoad, atPaint: at() });""")
        self.assertEqual(o["atLoad"], {"top": "8px", "right": "8px", "painted": False})
        self.assertEqual(o["atPaint"], {"top": "42px", "right": "8px", "painted": True},
                         "below the chips' row (14 + 20 + 8): the chips count, not the heads' boxes (round 1 went below the heads, 49 px); the step left "
                         "past the third chip (120 px) is longer than the step down (34 px)")

    # round 2, tests-2: every kind of control ruling A names, each alone (cursor auto, the one selector entry) at the badge's first
    # place where the search counts it, outside the list; the list is spelled here from the body's definition, not read from the
    # kernel's RCTL, so an entry dropped there fails here (round 3 added the two resize handles by id, each a control during its own
    # drag whatever its cursor). And the fixed half of the test for what stays put inside the list: a fixed element in the list
    # holding a control
    CONTROLS =["a[href]", "button", "input", "select", "textarea", "summary", "label", "[role=button]", "[data-act]", "[tabindex]", "[draggable=true]",
                "#composer-resize", "#tabbar-resize"]

    def test_each_kind_of_control_alone_moves_the_badge_off_it(self):
        for sel in self.CONTROLS:
            with self.subTest(sel):
                o = self._fit(r"""
add(null, [300, 54, 60, 20], { sel: %s });
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""" % json.dumps(sel))
                self.assertEqual(o["atPaint"], {"top": "82px", "right": "8px", "painted": True}, sel + ": counted, the badge goes below it (54 + 20 + 8)")
        o = self._fit(r"""
add(null, [300, 54, 60, 20]);
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True}, "the witness: the same element with no selector entry and no cursor is not a control")

    # Ruling 3 at 79dce614c (2026-10-04): a resize cursor makes a control, as a pointer or grab cursor does (the composer's resize
    # handle and the tab strip's have that cursor and nothing else). The keyword list is CSS's, the cursor property's values in CSS
    # Basic User Interface Level 4, and the resize cursors are derived from it, the keywords that end in -resize; each keyword is
    # tried alone, on an element at the badge's first place outside the list with no selector entry, so the product's list is
    # checked against the whole of CSS's: a keyword it drops, or one it adds, fails here
    CSS_CURSORS = ["auto", "default", "none", "context-menu", "help", "pointer", "progress", "wait", "cell", "crosshair", "text",
                   "vertical-text", "alias", "copy", "move", "no-drop", "not-allowed", "grab", "grabbing", "e-resize", "n-resize",
                   "ne-resize", "nw-resize", "s-resize", "se-resize", "sw-resize", "w-resize", "ew-resize", "ns-resize", "nesw-resize",
                   "nwse-resize", "col-resize", "row-resize", "all-scroll", "zoom-in", "zoom-out"]

    def test_a_pointer_grab_or_resize_cursor_alone_makes_a_control_and_no_other_cursor_does(self):
        resize = [k for k in self.CSS_CURSORS if k.endswith("-resize")]
        self.assertEqual(len(resize), 14, "CSS's resize cursors: the eight edges and corners, the four two-way ones, col and row: %r" % (resize,))
        counted = {"pointer", "grab", "grabbing"} | set(resize)
        for k in self.CSS_CURSORS:
            with self.subTest(k):
                o = self._fit(r"""
add(null, [300, 54, 60, 20], { cursor: %s });
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""" % json.dumps(k))
                if k in counted:
                    self.assertEqual(o["atPaint"], {"top": "82px", "right": "8px", "painted": True}, k + ": a control, the badge goes below it (54 + 20 + 8)")
                else:
                    self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True}, k + ": not a control, the first place")

    def test_on_a_short_list_the_composers_resize_handle_sends_the_badge_to_a_place_clear_of_it(self):
        # the landscape phone with the keyboard up (ruling 3): the list 28 px tall below the header, the composer's resize handle (7 px
        # across the whole width over the composer's top edge, a resize cursor and nothing else) over the list's bottom, the composer's
        # text field below. At 79dce614c the handle was not a control and the first place, 8 px below the list's top, covered it
        o = self._fit(r"""
shortList(169, 89); resize(61);
add(null, [0, 0, 390, 45], { sel: 'button' });                        // the header's session picker, across the page
add(null, [0, 86, 390, 7], { cursor: 'ns-resize' });                  // the composer's resize handle, across the page
add(null, [0, 100, 390, 60], { sel: 'textarea' });                    // its text field
const atLoad = at();
fire('romp:wsdown'); after(RHOLD_T);
out({ atLoad, atPaint: at() });""")
        self.assertEqual(o["atLoad"], {"top": "69px", "right": "8px", "painted": False})
        self.assertEqual(o["atPaint"], {"top": "53px", "right": "8px", "painted": True},
                         "8 px below the header (45 + 8), clear of everything: the first place (69 px) covers the handle's top 7 px, the walk "
                         "below it passes the list's bottom and the handle spans the width, so the clear place in the view is taken "
                         "(79dce614c: 69 px, over the handle)")

    # The same rule in the served recorder (ruling 3 at 79dce614c: a resize cursor makes a control in rctl and in the recorder alike).
    # The served legs reach the recorder's rule through one resize keyword, the composer's handle's ns-resize, so a recorder that
    # dropped col-resize and row-resize passed them. Here CSS's keywords run through both rules, the regular expression rctl tests in
    # the script _pane_spin returns and the recorder's CURSOR, executed in node, and each must count the same 17: pointer, grab,
    # grabbing and the 14 resize cursors. Since round 3 (2026-10-04) both rules count a cursor only where the element sets it, where
    # it differs from its parent's, and both name the two resize handles: the drag cases below execute rctl's half, and the served
    # legs of the two handle drags (test_return_from_background_served.py, _handle_drag_surface) execute the recorder's; the text
    # checks here keep the two rules one rule, and say nothing on their own about behaviour
    def test_the_served_recorder_counts_a_cursor_as_a_control_exactly_when_rctl_does(self):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node not installed")
        js = km._pane_spin("content", "live-ask")
        script = js[js.index("<script>") + len("<script>"):js.index("</script>")]
        mine = re.findall(r"function rctl\(e,s,u\)\{return \(e\.matches&&e\.matches\(RCTL\)\)\|\|\((/[^/\n]+/[a-z]*)\.test\(s\.cursor\)&&s\.cursor!==\(u\|\|getComputedStyle\(e\.parentElement\)\)\.cursor\);\}", script)
        self.assertEqual(len(mine), 1, "rctl's cursor rule is found once in the loader script, compared with the parent's cursor")
        self.assertEqual(script.count(".test(s.cursor)"), 1, "and it is the only cursor rule the loader script tests")
        self.assertEqual(script.count("rctl(e,s,M&&M.get(e.parentElement))"), 1, "robs hands rctl the parent's style from the scan's map")
        with open(os.path.join(HERE, "return_from_background_browser.mjs"), encoding="utf-8") as f:
            rec = f.read()
        theirs = re.findall(r"^\s*const CURSOR = (/[^/\n]+/[a-z]*);$", rec, re.M)
        self.assertEqual(len(theirs), 1, "the recorder's CURSOR is found once")
        self.assertEqual(re.findall(r"[\w.]+\.test\(cs\.cursor\)", rec), ["CURSOR.test(cs.cursor)"], "the recorder's control test reads CURSOR, and no other cursor rule")
        self.assertEqual(rec.count("if (!el.matches(CONTROL) && !(CURSOR.test(cs.cursor) && cs.cursor !== getComputedStyle(el.parentElement).cursor)) continue;"), 1,
                         "the recorder counts a cursor where it differs from the parent's, as rctl does (executed in the served handle drag legs)")
        rctl_list = re.findall(r"var RCTL='([^']*)'", script)
        control = re.findall(r'^\s*const CONTROL = "([^"]*)";$', rec, re.M)
        self.assertEqual((len(rctl_list), len(control)), (1, 1), "RCTL and the recorder's CONTROL are found once each")
        for handle in ("#composer-resize", "#tabbar-resize"):
            self.assertIn(handle, rctl_list[0].split(","), "RCTL names " + handle + " (executed in the drag cases below)")
            self.assertIn(handle, [x.strip() for x in control[0].split(",")], "the recorder's CONTROL names " + handle)
        fx = tempfile.mkdtemp()
        path = os.path.join(fx, "cursors.js")
        with open(path, "w") as f:
            f.write("const K = %s, R = %s, C = %s;\nconsole.log(JSON.stringify({ rctl: C.filter((c) => K.test(c)), recorder: C.filter((c) => R.test(c)) }));\n"
                    % (mine[0], theirs[0], json.dumps(self.CSS_CURSORS)))
        r = subprocess.run([node, path], capture_output=True, text=True, timeout=30)
        shutil.rmtree(fx, ignore_errors=True)
        self.assertEqual(r.returncode, 0, r.stderr[:800])
        o = json.loads(r.stdout.strip().splitlines()[-1])
        counted = ["pointer", "grab", "grabbing"] + [k for k in self.CSS_CURSORS if k.endswith("-resize")]
        self.assertEqual(len(counted), 17)
        self.assertEqual(sorted(o["rctl"]), sorted(counted), "rctl counts pointer, grab, grabbing and the 14 resize cursors, and no other keyword")
        self.assertEqual(sorted(o["recorder"]), sorted(o["rctl"]), "the served recorder counts exactly the keywords rctl counts")

    # Round 3 (2026-10-04, correctness-1 and regression-1): a cursor counts only where an element sets it. During a drag of the
    # composer's resize handle the chat puts composer-resizing on the body, and during a drag of the tab strip's, tabbar-resizing;
    # each sets cursor: ns-resize there, and cursor inherits, so every element that sets no cursor of its own computes ns-resize
    # (bodyCursor). At 94f85bca3 rctl tested the computed cursor, so mid-drag the loader's full-view sheet (#pane-spin, fixed over the
    # whole view, faded but shown), the viewer's sticky header and a scroll-marks column counted as controls, and the painted badge
    # left its place for the drag. Each drag: pointerdown (the class on the body, which the watch sees and scans for), the drag's
    # moves, pointerup. The composer's drag shrinks it: each move writes the text field's height, and the list's bottom follows the
    # composer down. Three places to hold: left of the viewer's pin (a left step) in each drag, and the first place below a
    # scroll-marks column the chat painted for the layout before the shrink, which the grown list now reaches past (the review's
    # page: at 94f85bca3 only the sheet covered that gap, so the fallback took it)
    _DRAG = r"""
const sheet = add(null, [0, 0, 390, 844], { position: 'fixed' });      // the loader's sheet (#pane-spin): fixed over the whole view, faded, shown
add(null, [0, 0, 390, 44], { sel: 'button' });                         // the header's session picker, across the page
const footer = add(null, [0, 704, 390, 140]);                          // the composer
const grip = add(footer, [0, 700, 390, 7], { cursor: 'ns-resize', sel: '#composer-resize' });   // its resize handle, over its top edge
const field = add(footer, [10, 712, 300, 120], { sel: 'textarea' });    // its text field, grown before the wait
const tgrip = add(null, [0, 40, 390, 6], { cursor: 'ns-resize', sel: '#tabbar-resize' });       // the strip's handle, over the header's bottom edge
const drag = (cls, moves) => { const p = {}; bodyCursor('ns-resize'); attr(document.body, 'class', cls); frame(); p.down = at();
  for (const dy of moves) { field.box[1] += dy; field.box[3] -= dy; grip.box[1] += dy; footer.box[1] += dy; footer.box[3] -= dy;
    const b = footer.box[1]; CONTENT.getBoundingClientRect = () => ({ top: CTOP, left: 0, right: 390, bottom: b }); attr(field, 'style'); frame(); }
  p.moved = at(); bodyCursor('auto'); attr(document.body, 'class', null); frame(); p.up = at(); return p; };
"""

    def test_a_resize_handles_drag_moves_the_painted_badge_nowhere(self):
        pin = "const head = add(CONTENT, [0, 52, 390, 31], { position: 'sticky' }); add(head, [360, 58, 20, 20], { sel: '[role=button]' });"
        marks = "add(null, [378, 44, 12, 660], { position: 'fixed' });             // the scroll marks' column over the list's right 12 px, painted for the list before the shrink"
        cases = [("left of the viewer's pin, the composer shrunk", pin, "composer-resizing", "[30, 30]", {"top": "52px", "right": "38px", "painted": True}),
                 ("left of the viewer's pin, the tab strip's handle held", pin, "tabbar-resizing", "[]", {"top": "52px", "right": "38px", "painted": True}),
                 ("the first place, the composer shrunk below a marks column painted before the shrink", marks, "composer-resizing", "[30, 30]",
                  {"top": "52px", "right": "8px", "painted": True})]
        for what, page, cls, moves, place in cases:
            with self.subTest(what):
                o = self._run(page + "\n" + self._DRAG + r"""
fire('romp:wsdown'); after(RHOLD_T); const atPaint = at();
const d = drag(%s, %s);
out({ atPaint, d, bottom: CONTENT.getBoundingClientRect().bottom });""" % (json.dumps(cls), moves), pre=self._PLACE_PRE + self._FIT_PRE)
                self.assertEqual(o["atPaint"], place, what + ": painted there")
                self.assertEqual(o["d"], {"down": place, "moved": place, "up": place},
                                 what + ": the class on the body (ns-resize, inherited by every element that sets no cursor) moves the badge nowhere at "
                                 "pointerdown, through the drag and at pointerup (94f85bca3: the sheet, the header and the marks column counted, and the "
                                 "badge took the fallback's place for the drag)")
                if cls == "composer-resizing":
                    self.assertEqual(o["bottom"], 764, what + ": the composer shrank 60 px and the list's bottom followed it")

    # ...and the handle under the drag stays a control: during its own drag a handle's cursor (ns-resize, its own) equals its parent's
    # (the body's class), so only RCTL's naming keeps it counted. Each handle here lies under the badge's first place, across the page
    # (the landscape phone with the keyboard up puts the composer's there); the badge sits below it at the paint and must stay below
    # it while the handle is dragged (with the parent rule and no naming, it went back to the first place, over the handle)
    def test_each_resize_handle_stays_a_control_during_its_own_drag(self):
        for cls, sel in (("composer-resizing", "#composer-resize"), ("tabbar-resizing", "#tabbar-resize")):
            with self.subTest(sel):
                o = self._fit(r"""
add(null, [0, 0, 390, 44], { sel: 'button' });                         // the header, across the page
add(null, [0, 56, 390, 7], { cursor: 'ns-resize', sel: %s });           // the handle, across the page, under the first place (52 to 77)
fire('romp:wsdown'); after(RHOLD_T); const atPaint = at();
bodyCursor('ns-resize'); attr(document.body, 'class', %s); frame(); const mid = at();
bodyCursor('auto'); attr(document.body, 'class', null); frame();
out({ atPaint, mid, up: at() });""" % (json.dumps(sel), json.dumps(cls)))
                below = {"top": "71px", "right": "8px", "painted": True}
                self.assertEqual(o["atPaint"], below, sel + ": painted below the handle (56 + 7 + 8)")
                self.assertEqual(o["mid"], below, sel + ": mid-drag the handle, whose cursor now equals its parent's, is still a control (RCTL names it)")
                self.assertEqual(o["up"], below, sel + ": and after the drag")

    def test_a_control_in_a_fixed_element_in_the_list_moves_the_badge_off_it(self):
        o = self._fit(r"""
const pop = add(CONTENT, [200, 50, 190, 40], { position: 'fixed' }); add(pop, [300, 54, 60, 20], { sel: 'button' });
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
        self.assertEqual(o["atPaint"], {"top": "82px", "right": "8px", "painted": True}, "a fixed element in the list stays put: its button counts (54 + 20 + 8)")

    def test_a_control_shown_by_a_style_change_alone_while_painted_moves_the_badge_off_it(self):
        # round 2, tests-3: the watch observes attributes (class, style, hidden), not only added elements: a control outside the list,
        # display:none at the paint, is shown by a style write and nothing else
        o = self._fit(r"""
const btn = add(null, [300, 54, 60, 20], { sel: 'button', display: 'none' });
fire('romp:wsdown'); after(RHOLD_T); const atPaint = at();
btn.cs.display = 'block'; attr(btn, 'style'); frame();
out({ atPaint, shown: at() });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True}, "hidden at the paint: not counted")
        self.assertEqual(o["shown"], {"top": "82px", "right": "8px", "painted": True}, "shown by its style alone: the badge goes below it (54 + 20 + 8)")

    def test_what_scrolls_with_the_list_or_holds_no_control_is_not_avoided(self):
        # a button in a message (content: it scrolls out from under the badge, ruling 9 of round 0) and a sticky element in the list
        # with no control in it (the chat's gap glyph) leave the badge in its first place
        o = self._fit(r"""
const row = add(CONTENT, [0, 50, 390, 80]); add(row, [300, 55, 60, 20], { sel: 'button' });
add(CONTENT, [0, 52, 390, 40], { position: 'sticky' });
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True})

    def test_a_scroll_while_painted_moves_the_badge_off_a_sticky_header_scrolling_into_its_place(self):
        o = self._fit(r"""
const head = add(CONTENT, [0, 300, 390, 29], { position: 'sticky' }); add(head, [300, 304, 80, 20], { sel: 'button' });   // its button at the right end
fire('romp:wsdown'); after(RHOLD_T); const atPaint = at();
head.box[1] = 60; ALL[2].box[1] = 64;                                 // the list scrolls: the header comes up under the badge
scroll(); frame(); const scrolled = at();
const reads = STYLE_READS; scroll(); frame(); const rereads = STYLE_READS - reads;
fire('romp:wsfresh'); const cleared = { painted: painted(), watching: mo(), scrollListeners: (DOCL.scroll || []).length };
change(head); frame(); const afterChange = { watching: mo(), scrollListeners: (DOCL.scroll || []).length };
out({ atPaint, scrolled, rereads, cleared, afterChange });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True})
        self.assertEqual(o["scrolled"], {"top": "92px", "right": "8px", "painted": True}, "the scroll moves it below the header's button (64 + 20 + 8)")
        self.assertLessEqual(o["rereads"], 1, "a scroll re-reads the boxes the last scan found; it does not scan the page's styles again")
        self.assertIs(o["cleared"]["painted"], False)
        self.assertEqual(o["afterChange"], {"watching": 0, "scrollListeners": 0}, "with the badge down, the frame the next change asks for ends the watch: no observer, no scroll listener")

    def test_a_column_of_controls_through_the_badges_column_sends_it_left_not_down_onto_them(self):
        # round 2, extra5-1: a column of controls outside the list, from 50 px to the page's bottom, under the badge's column. The
        # walk that prefers the shorter step goes down the column (each step down, 50 px, is shorter than the 90 px step left) and
        # passes the list's bottom; at a4262a94d the fallback then weighed only places at the right edge, each over the column or
        # the header's control, and took the least covered of them, over both. A second walk from the first place steps left
        # wherever the badge fits
        o = self._fit(r"""
add(null, [0, 0, 390, 44], { sel: 'button' });                        // the header's session picker, across the page
for (let y = 50; y < 844; y += 22) add(null, [300, y, 80, 22], { sel: 'button' });
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "98px", "painted": True},
                         "one step left of the column (390 - 300 + 8), at the first place's height, clear (a4262a94d: 39 px at the right edge, over the header's "
                         "control and the column)")

    def test_the_end_of_a_transition_re_reads_the_boxes_while_painted(self):
        # round 2, open call 7: the scroll marks move to their new places by a 180 ms CSS transition, which no change to the page or
        # scroll reports, and WebKit read them mid-move at the scroll. The painted badge is placed again at the end of a transition
        # (a transitionend listener on the document, capturing): a re-read, no scan, at the next frame
        o = self._fit(r"""
const mark = add(null, [381, 300, 8, 2], { sel: '[data-act]' });
fire('romp:wsdown'); after(RHOLD_T); const atPaint = at();
mark.box[1] = 60;                                                     // the mark ends its move under the badge
const reads = STYLE_READS; transition(); const beforeFrame = at(); frame(); const ended = { place: at(), reads: STYLE_READS - reads };
fire('romp:wsfresh'); change(CONTENT); frame();
out({ atPaint, beforeFrame, ended, listenersAfter: (DOCL.transitionend || []).length });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True})
        self.assertEqual(o["beforeFrame"], {"top": "52px", "right": "8px", "painted": True})
        self.assertEqual(o["ended"], {"place": {"top": "52px", "right": "17px", "painted": True}, "reads": 1},
                         "at the frame after the transition ends, the badge goes left of the mark where it now is (390 - 381 + 8), with no scan")
        self.assertEqual(o["listenersAfter"], 0, "with the badge down, the watch's end removes the transitionend listener")

    # What an overflow container hides does not count (round 2, correctness-1, 2026-10-03). The desktop chat's tab strip (#tabbar,
    # max-height 150 px, overflow-y auto) and the pinned-notes strip (max-height min(11em, 30vh), overflow-y auto) scroll what does
    # not fit out of view; the rows they hide lie below them, over the list's top, and at a4262a94d they still counted: the badge
    # stepped down past controls nobody could see, and on a short pane it took the fallback onto a visible one. Each control now
    # counts by its box clipped by the ancestors whose overflow clips it (rclip, rvis). `strip(...)` builds such a strip: rows of
    # controls at the right end, every 22 px from `top`, inside a box `h` tall; with `overflow` 'visible' the same rows show, the
    # case's witness that the hidden rows do lie over the badge's first place.
    _STRIP = r"""
const strip = (top, h, rows, overflow, row) => { const s = add(null, [0, top, 390, h], { overflowY: overflow, overflowX: overflow === 'visible' ? 'visible' : 'hidden' });
  for (let i = 0; i < rows; i++) { const y = top + 4 + 22 * i; row(s, y); } return s; };
const tabRow = (s, y) => { add(s, [12, y, 220, 20], { cursor: 'pointer' }); add(s, [236, y, 150, 20], { cursor: 'pointer' }); };   // two tabs, the second reaching the badge's column (248 to 382)
const noteRow = (s, y) => { const line = add(s, [24, y, 342, 20]); add(line, [270, y + 2, 44, 16], { sel: 'button' }); add(line, [318, y + 2, 46, 16], { sel: 'button' }); };   // a note's details and unpin buttons
"""

    def _strip_fit(self, scenario):
        return self._run(scenario, pre=self._PLACE_PRE + self._FIT_PRE + self._STRIP)

    def test_tabs_the_desktop_tab_strip_scrolls_out_of_view_do_not_count(self):
        # the tab strip across the pane's top, 44 px tall here (its cap), with eight rows of tabs: the first two show, the six below
        # it are hidden by its overflow and lie over the transcript from 48 px down, the badge's first place (52 px) among them
        for overflow in ("auto", "visible"):
            with self.subTest(overflow=overflow):
                o = self._strip_fit(r"""
strip(0, 44, 8, '%s', tabRow);
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""" % overflow)
                if overflow == "auto":
                    self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True},
                                     "the first place, 8 px below the transcript's top: every tab under it is hidden by the strip (a4262a94d stepped it "
                                     "down past all six hidden rows, to 186 px)")
                else:
                    self.assertEqual(o["atPaint"]["top"], "186px", "the witness: the same rows shown (overflow visible) do lie over the first place, and "
                                     "the badge steps below the last (4 + 7 x 22 + 20 + 8)")

    def test_notes_the_pinned_notes_strip_scrolls_out_of_view_do_not_count(self):
        # the phone: the header (44 px), then the pinned-notes strip, 60 px tall here, with eight rows; two and a half show, and the
        # rest lie over the transcript, which starts at 104 px, each with its details and unpin buttons in the badge's column
        o = self._strip_fit(r"""
resize(104);
add(null, [0, 0, 390, 44], { sel: 'button' });                        // the header's session picker
strip(44, 60, 8, 'auto', noteRow);
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
        self.assertEqual(o["atPaint"], {"top": "112px", "right": "8px", "painted": True},
                         "the first place, 8 px below the transcript's top (104 + 8): the rows below the strip's bottom are hidden by it")

    def test_hidden_rows_on_a_short_pane_leave_the_badge_at_its_clear_first_place_not_on_a_visible_control(self):
        # a short chat pane: the tab strip shows two tabs at the right end and hides the rows below them, which lie over the whole
        # transcript (44 to 120 px) and past it; the composer's text field is below. At a4262a94d the walk found no clear place,
        # since it counted the hidden rows, and the fallback put the badge over the two tabs that show
        o = self._strip_fit(r"""
shortList(200, 120);
const s = add(null, [0, 0, 390, 44], { overflowY: 'auto', overflowX: 'hidden' });
add(s, [300, 4, 60, 14], { cursor: 'pointer' }); add(s, [300, 30, 60, 12], { cursor: 'pointer' });   // the two tabs that show
for (let y = 48; y < 140; y += 22) add(s, [236, y, 150, 22], { cursor: 'pointer' });                  // the rows the strip hides
add(null, [0, 124, 390, 60], { sel: 'textarea' });
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True},
                         "the first place, which covers nothing a person can see (a4262a94d took 15 px, over both visible tabs)")

    def test_overflow_clips_along_the_containing_blocks_so_a_fixed_or_escaping_absolute_control_still_counts(self):
        # overflow clips an element only through the chain of its containing blocks: a fixed control escapes every ancestor that
        # is not its containing block, and an absolute one escapes the ancestors between it and its positioned containing block.
        # Each scenario puts one control over the first place (52 to 77 px) inside a box whose overflow is hidden and which ends
        # at 44 px
        cases = [
            ("a fixed control inside the strip escapes it", "const s = add(null, [0, 0, 390, 44], { overflow: 'hidden' }); add(s, [300, 54, 60, 20], { position: 'fixed', sel: 'button' });", "82px"),
            ("an absolute control whose containing block is outside the strip escapes it",
             "const w = add(null, [0, 0, 390, 300], { position: 'relative' }); const s = add(w, [0, 0, 390, 44], { overflow: 'hidden' }); add(s, [300, 54, 60, 20], { position: 'absolute', sel: 'button' });", "82px"),
            ("an absolute control in a positioned strip is clipped by it",
             "const s = add(null, [0, 0, 390, 44], { overflow: 'hidden', position: 'relative' }); add(s, [300, 54, 60, 20], { position: 'absolute', sel: 'button' });", "52px"),
            ("a fixed control in a transformed strip is clipped by it (the transform makes the strip its containing block)",
             "const s = add(null, [0, 0, 390, 44], { overflow: 'hidden', transform: 'translateZ(0)' }); add(s, [300, 54, 60, 20], { position: 'fixed', sel: 'button' });", "52px"),
            ("contain:paint clips as overflow does", "const s = add(null, [0, 0, 390, 44], { contain: 'paint' }); add(s, [300, 54, 60, 20], { sel: 'button' });", "52px"),
            ("a strip clipping across only leaves a control below it counted", "const s = add(null, [0, 0, 390, 44], { overflowX: 'clip', overflowY: 'visible' }); add(s, [300, 54, 60, 20], { sel: 'button' });", "82px"),
            ("an inline box clips nothing", "const s = add(null, [0, 0, 390, 44], { overflow: 'hidden', display: 'inline' }); add(s, [300, 54, 60, 20], { sel: 'button' });", "82px"),
        ]
        for what, page, top in cases:
            with self.subTest(what):
                o = self._strip_fit(page + r"""
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
                self.assertEqual(o["atPaint"], {"top": top, "right": "8px", "painted": True},
                                 what + (": counted, the badge goes 8 px below it (54 + 20 + 8)" if top == "82px" else ": not counted, the first place"))

    def test_the_containing_block_chain_runs_through_the_controls_ancestors_and_what_makes_a_containing_block(self):
        # the rehearsed check of round 2 (2026-10-04): the case above sets the position on the control itself, and nothing pinned
        # the walk's next step, from each containing block to its own containing block, so a static control inside a fixed or
        # absolute wrapper was judged by its own position alone and counted as clipped by the strip its wrapper escapes, which
        # would leave the badge over a control a person can see. Nor was it pinned that display:contents clips nothing, or that
        # contain:layout, will-change:transform and a filter each make a containing block, as a transform does. Each scenario
        # puts one control over the first place (52 to 77 px) inside a box whose overflow is hidden and which ends at 44 px
        cases = [
            ("a static control in a fixed wrapper inside the strip escapes it with its wrapper",
             "const s = add(null, [0, 0, 390, 44], { overflow: 'hidden' }); const w = add(s, [200, 50, 190, 40], { position: 'fixed' }); add(w, [300, 54, 60, 20], { sel: 'button' });",
             "82px"),
            ("a static control in an absolute wrapper whose containing block is outside the strip escapes it with its wrapper",
             "const r = add(null, [0, 0, 390, 300], { position: 'relative' }); const s = add(r, [0, 0, 390, 44], { overflow: 'hidden' }); "
             "const w = add(s, [200, 50, 190, 40], { position: 'absolute' }); add(w, [300, 54, 60, 20], { sel: 'button' });",
             "82px"),
            ("a static control in a fixed wrapper inside a transformed strip is clipped by it (the strip is the wrapper's containing block)",
             "const s = add(null, [0, 0, 390, 44], { overflow: 'hidden', transform: 'translateZ(0)' }); const w = add(s, [200, 50, 190, 40], { position: 'fixed' }); "
             "add(w, [300, 54, 60, 20], { sel: 'button' });",
             "52px"),
            ("display:contents clips nothing", "const s = add(null, [0, 0, 390, 44], { overflow: 'hidden', display: 'contents' }); add(s, [300, 54, 60, 20], { sel: 'button' });", "82px"),
            ("contain:layout makes the strip a fixed control's containing block, so the strip clips it",
             "const s = add(null, [0, 0, 390, 44], { overflow: 'hidden', contain: 'layout' }); add(s, [300, 54, 60, 20], { position: 'fixed', sel: 'button' });", "52px"),
            ("will-change:transform makes the strip a fixed control's containing block, so the strip clips it",
             "const s = add(null, [0, 0, 390, 44], { overflow: 'hidden', willChange: 'transform' }); add(s, [300, 54, 60, 20], { position: 'fixed', sel: 'button' });", "52px"),
            ("a filter makes the strip a fixed control's containing block, so the strip clips it",
             "const s = add(null, [0, 0, 390, 44], { overflow: 'hidden', filter: 'blur(1px)' }); add(s, [300, 54, 60, 20], { position: 'fixed', sel: 'button' });", "52px"),
        ]
        for what, page, top in cases:
            with self.subTest(what):
                o = self._strip_fit(page + r"""
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
                self.assertEqual(o["atPaint"], {"top": top, "right": "8px", "painted": True},
                                 what + (": counted, the badge goes 8 px below it (54 + 20 + 8)" if top == "82px" else ": not counted, the first place"))

    # Round 3 (2026-10-04, tests-3): the clip's parts that no case reached. A perspective, a will-change of perspective or of filter,
    # and contain strict or content each make the strip a fixed control's containing block, so the strip, whose overflow is hidden,
    # clips it; contain strict and content each clip a static control as overflow does; and a control is cut to the strip's padding
    # box, inside its border and scrollbar (clientLeft, clientTop, clientWidth, clientHeight), on each axis. Each scenario puts one
    # control or two over the first place (52 to 77 px, from 248 to 382 px across) where the strip lets none of it be seen, so the
    # badge keeps its first place, except the second padding-box case, where the strip leaves 6 px of the control in view; and a
    # witness, an unclipped fixed control, which moves it
    def test_perspective_will_change_containment_and_the_padding_box_on_both_axes_clip(self):
        fixed = "const s = add(null, [0, 0, 390, 44], { overflow: 'hidden', %s }); add(s, [300, 54, 60, 20], { position: 'fixed', sel: 'button' });"
        clip = "const s = add(null, [0, 0, 390, 44], { %s }); add(s, [300, 54, 60, 20], { sel: 'button' });"
        cases = [
            ("a perspective makes the strip a fixed control's containing block, so the strip clips it", fixed % "perspective: '500px'", "52px"),
            ("will-change:perspective makes the strip a fixed control's containing block", fixed % "willChange: 'perspective'", "52px"),
            ("will-change:filter makes the strip a fixed control's containing block", fixed % "willChange: 'filter'", "52px"),
            ("contain:strict makes the strip a fixed control's containing block", fixed % "contain: 'strict'", "52px"),
            ("contain:content makes the strip a fixed control's containing block", fixed % "contain: 'content'", "52px"),
            ("contain:strict clips as overflow does", clip % "contain: 'strict'", "52px"),
            ("contain:content clips as overflow does", clip % "contain: 'content'", "52px"),
            ("the strip's padding box ends 10 px above its border box's bottom (a border or a scrollbar), over a control from 50 to 80 px",
             "const s = add(null, [0, 0, 390, 60], { overflow: 'hidden', clientHeight: 50 }); add(s, [300, 50, 60, 30], { sel: 'button' });", "52px"),
            ("the strip's padding box starts 10 px below its top (a border) and is 30 px tall: 6 px of a control from 54 to 74 px show",
             "const s = add(null, [0, 20, 390, 50], { overflow: 'hidden', clientTop: 10, clientHeight: 30 }); add(s, [300, 54, 60, 20], { sel: 'button' });", "68px"),
            ("across: the strip's padding box starts 20 px inside its left edge and is 100 px wide, over a control in its left border and one in its right",
             "const s = add(null, [250, 40, 140, 60], { overflow: 'hidden', clientLeft: 20, clientWidth: 100 }); add(s, [252, 54, 16, 20], { sel: 'button' }); "
             "add(s, [372, 54, 16, 20], { sel: 'button' });", "52px"),
            ("the witness: a fixed control in a strip that makes no containing block escapes it", fixed % "contain: 'none'", "82px"),
        ]
        for what, page, top in cases:
            with self.subTest(what):
                o = self._strip_fit(page + r"""
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
                self.assertEqual(o["atPaint"], {"top": top, "right": "8px", "painted": True},
                                 what + {"52px": ": none of it can be seen, the first place", "68px": ": the 6 px that show (54 to 60) send the badge below them (60 + 8)",
                                         "82px": ": counted, the badge goes 8 px below it (54 + 20 + 8)"}[top])

    def test_a_scroll_re_reads_the_clip_of_the_controls_the_last_scan_found(self):
        # a panel outside the list whose overflow hides all but the top 10 px of a control that reaches over the first place; a scroll
        # (the panel growing as its own content scrolls, say) shows the control whole, and the scroll's re-read, which scans no style,
        # moves the badge off it
        o = self._strip_fit(r"""
const panel = add(null, [200, 40, 190, 10], { overflow: 'hidden' }); add(panel, [300, 40, 60, 40], { sel: 'button' });
fire('romp:wsdown'); after(RHOLD_T); const atPaint = at();
panel.box[3] = 40; const reads = STYLE_READS; scroll(); frame(); const scrolled = at();
out({ atPaint, scrolled, reads: STYLE_READS - reads });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True}, "the control's visible 10 px (40 to 50) does not reach the first place")
        self.assertEqual(o["scrolled"], {"top": "88px", "right": "8px", "painted": True}, "shown whole by the panel's new box, the control moves the badge below it (80 + 8)")
        self.assertLessEqual(o["reads"], 1, "the scroll re-read the boxes and the clip, and scanned no style")

    # The watch's cost (round 2, 2026-10-03: regression-1 and open call 10). At a4262a94d every change anywhere in the body scanned the
    # whole page while the badge was painted, one style read per element, and a chat changes the page at each second's tick and at
    # each keystroke. Now a change or a scroll asks for one placement at the next animation frame; the watch observes the list's own
    # children and attributes, each sticky or fixed element in it, and the page outside it, never the rest of the list's content;
    # and only a change that can add a control scans again (an element added to an element the last scan did not hold, or an
    # attribute changed on an element the last scan did not hold or that holds elements), every other one re-reads the boxes. A scan reads every element's style once and
    # the body's (since round 3, which compares the cursor of each of the body's own children with the body's), and the placement reads
    # the list's own once more, the scroll-area test, so a placement with no scan makes one read.
    _PAGE = r"""
const header = add(null, [0, 0, 390, 44], { sel: 'button' }); header.id = 'header';
const head = add(CONTENT, [0, 300, 390, 29], { position: 'sticky' }); head.id = 'head'; add(head, [300, 304, 80, 20], { sel: 'button' });
const row = add(CONTENT, [0, 400, 390, 80]); row.id = 'row'; const inRow = add(row, [10, 410, 200, 20]); inRow.id = 'inRow';
const footer = add(null, [0, 760, 390, 84]); footer.id = 'footer';
const timer = add(footer, [10, 764, 60, 16]); timer.id = 'timer';                      // the status line's work timer: text, no control
const field = add(footer, [10, 784, 300, 40], { sel: 'textarea' }); field.id = 'field';  // the composer's text field: a control with no element in it
const send = add(footer, [320, 784, 60, 40], { sel: 'button' }); send.id = 'send'; add(send, [340, 794, 20, 20]);   // a button that holds an icon
let ASKS = 0; { const raf = global.requestAnimationFrame; global.requestAnimationFrame = (fn) => { ASKS++; return raf(fn); }; }
const scan = () => ALL.length + 2;                                                      // the style reads of a placement that scans: each element's, the body's and the list's again
"""

    def _watch_fit(self, scenario):
        return self._run(scenario, pre=self._PLACE_PRE + self._FIT_PRE + self._PAGE)

    def test_the_watch_places_the_badge_once_a_frame_however_many_changes_and_scrolls_arrive(self):
        o = self._watch_fit(r"""
fire('romp:wsdown'); after(RHOLD_T); const atPaint = at();
const notice = add(null, [42, 54, 307, 29], { cursor: 'pointer' });
const reads = STYLE_READS, asks = ASKS;
added(notice); change(CONTENT); scroll(); attr(field); text(timer); scroll(); added(add(null, [0, 600, 10, 10]));
const beforeFrame = { place: at(), reads: STYLE_READS - reads, asks: ASKS - asks };
frame(); const afterFrame = { place: at(), reads: STYLE_READS - reads, asks: ASKS - asks };
out({ atPaint, beforeFrame, afterFrame, scan: scan() });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True})
        self.assertEqual(o["beforeFrame"], {"place": {"top": "52px", "right": "8px", "painted": True}, "reads": 0, "asks": 1},
                         "seven changes and scrolls in one frame ask for one frame and read nothing in their own tasks")
        self.assertEqual(o["afterFrame"], {"place": {"top": "91px", "right": "8px", "painted": True}, "reads": o["scan"], "asks": 1},
                         "the frame places the badge once, with one scan (an element was added), below the notice (54 + 29 + 8)")

    def test_a_frame_scans_when_any_request_in_it_asked_for_a_scan_whatever_the_order(self):
        # the rehearsed check of round 2 (2026-10-04): a jump in the chat inserts the landing notice before the transcript and
        # scrolls it in the same task, so one frame gets a request that needs a scan (the notice added) and one that needs only a
        # re-read (the scroll), in either order. The case above ends its frame on a scan request and starts it with one, so a
        # frame that kept only the last request's kind, or only the first's, passed it; either would re-read alone here, and the
        # badge would stay over the only control that cancels the jump
        for order in ("notice, then scroll", "scroll, then notice"):
            with self.subTest(order):
                o = self._watch_fit(r"""
fire('romp:wsdown'); after(RHOLD_T); const atPaint = at();
const notice = add(null, [42, 54, 307, 29], { cursor: 'pointer' });
const reads = STYLE_READS, asks = ASKS;
if (%s) { added(notice); scroll(); } else { scroll(); added(notice); }
frame();
out({ atPaint, placed: { place: at(), reads: STYLE_READS - reads, asks: ASKS - asks }, scan: scan() });""" % ("true" if order.startswith("notice") else "false"))
                self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True})
                self.assertEqual(o["placed"], {"place": {"top": "91px", "right": "8px", "painted": True}, "reads": o["scan"], "asks": 1},
                                 order + " in one frame: one frame asked for, and it scans, so the badge goes below the notice (54 + 29 + 8)")

    def test_a_resize_in_a_frame_the_watch_already_placed_the_badge_in_asks_for_its_scan_at_the_next_frame(self):
        # the rehearsed check of round 2 (2026-10-04): the resize observer placed the painted badge at once, with a scan, after the
        # frame's own placement, so a frame in which the container resized held two placements (in the lab chat each Shift+Enter
        # that grew the composer gave a frame with a re-read and then a scan of every element). An engine runs a frame's animation
        # frame callbacks, lays the page out, then runs its resize observer callbacks (engineFrame, below). The resize callback now
        # places the painted badge at once only when the container's box or the view's size differs from what the last placement
        # read; when the frame's own placement already read them, it asks for the scan at the next frame instead (a resize can show
        # a control by a media query alone, which no change to the page reports, so the scan is kept). Each placement while
        # painted reads the badge's box once (fits)
        o = self._watch_fit(r"""
fire('romp:wsdown'); after(RHOLD_T);
let fits = 0; { const g = BADGE.getBoundingClientRect; BADGE.getBoundingClientRect = () => { fits++; return g(); }; }
const engineFrame = (resized) => task(() => { FRAMES.splice(0).forEach((fn) => fn && fn(NOW)); if (resized) ROS.forEach((cb) => cb([])); });
const step = (fn, resized) => { const reads = STYLE_READS, asks = ASKS; fits = 0; fn(); engineFrame(resized); return { fits, reads: STYLE_READS - reads, asks: ASKS - asks, place: at() }; };
// the composer grows by a line (its style written) and the list's bottom rises with it: the change's frame, the list resized in it
const grew = step(() => { field.box = [10, 744, 300, 80]; CONTENT.getBoundingClientRect = () => ({ top: CTOP, left: 0, right: 390, bottom: 660 }); attr(field, 'style'); }, true);
const next = step(() => {}, false);
// the view resized with no change the watch sees (a window resize, the pane shown): the resize callback's frame, nothing asked before it
const resized = step(() => { document.documentElement.clientHeight = 800; }, true);
const quiet = step(() => {}, false);
out({ grew, next, resized, quiet, scan: scan() });""")
        at52 = {"top": "52px", "right": "8px", "painted": True}
        self.assertEqual(o["grew"], {"fits": 1, "reads": 1, "asks": 2, "place": at52},
                         "the composer's growth: one placement in its frame, the watch's re-read (one read), and the resize callback, finding the box that "
                         "placement read, asks for a frame (6904c6db4: two placements, the re-read and then a scan)")
        self.assertEqual(o["next"], {"fits": 1, "reads": o["scan"], "asks": 0, "place": at52}, "the next frame places it once, with the resize's scan")
        self.assertEqual(o["resized"], {"fits": 1, "reads": o["scan"], "asks": 0, "place": at52},
                         "a resize no placement has read yet: the resize callback places it at once, in that frame, with a scan, and asks for no frame")
        self.assertEqual(o["quiet"], {"fits": 0, "reads": 0, "asks": 0, "place": at52}, "and nothing is left asked for")

    def test_the_watch_observes_the_list_its_sticky_elements_and_the_page_outside_it_never_the_lists_other_content(self):
        o = self._watch_fit(r"""
fire('romp:wsdown'); after(RHOLD_T);
const nm = (t) => (t === document.body ? 'body' : t === CONTENT ? 'list' : t.id || '?');
const regs = watchers()[0].regs.map((r) => [nm(r.t), !!r.o.childList, !!r.o.subtree, !!r.o.attributes, !!r.o.attributeOldValue, (r.o.attributeFilter || []).join(',')]).sort();
const reads = STYLE_READS, asks = ASKS;
change(row); attr(inRow, 'class'); text(inRow); frame();
out({ regs, deep: { reads: STYLE_READS - reads, asks: ASKS - asks } });""")
        F = "class,style,hidden"
        self.assertEqual(o["regs"], sorted([["body", True, False, True, True, F], ["list", True, False, True, True, F], ["head", True, True, True, True, F],
                                            ["header", True, True, True, True, F], ["footer", True, True, True, True, F]]),
                         "the list (its children and attributes), its sticky element with all it holds, the body's own children and attributes, and every "
                         "other child of the body with all it holds, each attribute record with the value it had; nothing observes the list's other "
                         "content, and neither the body nor the list is observed with all it holds")
        self.assertEqual(o["deep"], {"reads": 0, "asks": 0}, "a change inside a message in the list wakes nothing")

    def test_the_status_lines_tick_and_the_composers_growth_re_read_the_boxes_and_scan_nothing(self):
        o = self._watch_fit(r"""
fire('romp:wsdown'); after(RHOLD_T);
let reads = STYLE_READS; text(timer); frame(); const tick = STYLE_READS - reads;
reads = STYLE_READS; attr(field, 'style'); frame(); const key = STYLE_READS - reads;
field.box = [200, 50, 180, 40]; reads = STYLE_READS; attr(field, 'style'); frame(); const grown = { place: at(), reads: STYLE_READS - reads };
out({ tick, key, grown });""")
        self.assertEqual(o["tick"], 1, "the timer's text written: a re-read (the scroll-area test's one read), no scan")
        self.assertEqual(o["key"], 1, "a style written on the composer's text field, a control the scan holds with no element in it: a re-read, no scan")
        self.assertEqual(o["grown"], {"place": {"top": "98px", "right": "8px", "painted": True}, "reads": 1},
                         "the re-read still moves the badge off the field when its new box reaches the badge (50 + 40 + 8), with no scan")

    def test_an_element_added_inside_a_control_the_scan_holds_re_reads_and_scans_nothing(self):
        # the chat's 1 s interval writes the status line's mode icon again (innerHTML on the icon's span inside its button): an element
        # added inside a control the scan holds, every box of it inside the part of that control a person can see, lies where the badge
        # already avoids; measured in the lab at f1a720ef2, one scan a second from that write alone
        o = self._watch_fit(r"""
fire('romp:wsdown'); after(RHOLD_T);
const step = (el) => { const reads = STYLE_READS; added(el); frame(); const n = STYLE_READS - reads; return { reads: n, scanned: n === scan() }; };
const icon = step(add(send, [340, 794, 20, 20]));
const svg = add(send, [342, 796, 16, 16]); add(svg, [344, 798, 12, 12]);
const deep = step(svg);
const unheld = step(add(footer, [80, 764, 40, 16]));
out({ icon, deep, unheld });""")
        self.assertEqual(o["icon"], {"reads": 1, "scanned": False}, "an element added inside the send button, a control the scan holds, its box inside the button's: a re-read, no scan")
        self.assertEqual(o["deep"], {"reads": 1, "scanned": False}, "an element holding another, both boxes inside the button's: a re-read, no scan")
        self.assertIs(o["unheld"]["scanned"], True, "an element added inside the footer, which the scan does not hold: a scan")

    # The round-3 build (2026-10-04): the held control a record's target lies in is the target or its nearest ancestor the scan holds
    # (rheld). The chat's status line writes its mode icon each second into a span inside the mode chip (span.meta-btn, cursor:
    # pointer), and the span only inherits the chip's cursor. Since a cursor counts only where it is set (round 3, correctness-1),
    # the span is no control of its own, and a watch that read the record's target alone scanned at each write (the build's lab
    # probe: one scan a second while painted, 4 of the 7 scans in ten wheel steps). Here the chip holds the icon's span, whose cursor
    # is inherited (bodyCursor computes it), and a write adds an element inside the span within the chip's box: a re-read. One that
    # reaches outside the chip scans, and so does the same write into a span of an element no scan holds
    def test_an_element_added_deep_inside_a_held_control_re_reads_as_one_added_to_it_does(self):
        o = self._watch_fit(r"""
const chip = add(footer, [80, 764, 90, 16], { cursor: 'pointer' }); chip.id = 'chip';   // the mode chip: its own pointer cursor
const ico = add(chip, [82, 765, 14, 14]); ico.id = 'ico';                              // the icon's span, no cursor of its own
const plain = add(footer, [200, 764, 40, 16]); const plainIco = add(plain, [202, 765, 14, 14]);   // a span in an element that is no control
bodyCursor('auto');                                                                    // the span inherits the chip's pointer
fire('romp:wsdown'); after(RHOLD_T);
const step = (target, box) => { const reads = STYLE_READS; deliver(kids(target, [add(target, box)], [])); frame(); const n = STYLE_READS - reads; return { reads: n, scanned: n === scan() }; };
const within = step(ico, [83, 766, 12, 12]);
const reaching = step(ico, [83, 700, 12, 12]);
const unheld = step(plainIco, [203, 766, 12, 12]);
out({ cursors: [chip.cs.cursor, ico.cs.cursor], within, reaching, unheld });""")
        self.assertEqual(o["cursors"], ["pointer", "pointer"], "the span computes the chip's pointer cursor, inherited")
        self.assertEqual(o["within"], {"reads": 1, "scanned": False}, "an icon written into the span inside the chip, within the chip's box: a re-read, no scan")
        self.assertIs(o["reaching"]["scanned"], True, "an element written into the span that reaches outside the chip: a scan")
        self.assertIs(o["unheld"]["scanned"], True, "the same write into a span of an element no scan holds: a scan")

    # Ruling 2 at 79dce614c (2026-10-04): an element added inside a held control re-reads only when every box of the added subtree lies
    # inside the part of that control a person can see (its box cut by the ancestors that clip it, rvis); one that reaches outside it,
    # such as a popup child of a control, scans as before, so a control it brings is found. The popup and the inner child each reach
    # out past the left and the top edge at once, so a test that dropped either comparison still scanned them; each edge is therefore
    # tried alone too, by a child within the button's span on the other axis, and so is a control no part of which can be seen
    def test_an_element_added_inside_a_held_control_that_reaches_outside_its_visible_box_scans(self):
        o = self._watch_fit(r"""
fire('romp:wsdown'); after(RHOLD_T);
const step = (el) => { const reads = STYLE_READS; added(el); frame(); const n = STYLE_READS - reads; return { reads: n, scanned: n === scan(), place: at() }; };
const popup = step(add(send, [250, 690, 130, 90], { position: 'absolute' }));          // a popup child above the button, reaching out of it
const wrapEl = add(send, [330, 790, 40, 28]); add(wrapEl, [240, 52, 140, 40], { sel: 'button' });   // inside the button, a child of it far outside
const inner = step(wrapEl);
const tabs = add(null, [0, 760, 390, 30], { overflow: 'hidden' }); const tab = add(tabs, [300, 770, 80, 40], { cursor: 'pointer' });   // a tab whose bottom 20 px the strip hides
added(tabs); frame();
const seen = step(add(tab, [310, 772, 20, 10]));
const clipped = step(add(tab, [310, 794, 20, 10]));
// one edge at a time; the send button is [320, 784, 60, 40]
const upOnly = step(add(send, [324, 724, 52, 56], { position: 'absolute' }));          // a popup that opens straight up, within the button's width
const rightOnly = step(add(send, [360, 790, 30, 20], { position: 'absolute' }));       // past the right edge alone, within the button's height
const leftOnly = step(add(send, [310, 790, 30, 20], { position: 'absolute' }));        // past the left edge alone, within the button's height
// a tab the strip scrolls wholly out of view (it starts at 400, right of the strip's 390 px): the scan holds it, and no part of it can be seen
const gone = add(tabs, [400, 765, 80, 20], { cursor: 'pointer' }); added(gone); frame();
const unseen = step(add(gone, [410, 768, 20, 10]));
out({ popup, inner, seen, clipped, upOnly, rightOnly, leftOnly, unseen });""")
        self.assertIs(o["popup"]["scanned"], True, "a popup child of the send button reaching above it: a scan, as before ruling 2's condition")
        self.assertEqual((o["inner"]["scanned"], o["inner"]["place"]), (True, {"top": "100px", "right": "8px", "painted": True}),
                         "an element inside the button whose own child reaches outside it: a scan, which finds that child's button and moves the badge "
                         "below it (52 + 40 + 8)")
        self.assertEqual((o["seen"]["reads"], o["seen"]["scanned"]), (1, False), "an element added inside the part of the tab the strip leaves in view: a re-read, no scan")
        self.assertIs(o["clipped"]["scanned"], True, "an element added inside the tab's box but in the part the strip hides: a scan, since it lies outside "
                      "the part of the tab a person can see")
        for k, why in (("upOnly", "a popup child that opens straight up from the send button, within its width: a scan (its top edge alone reaches out)"),
                       ("rightOnly", "a child that reaches past the send button's right edge alone: a scan"),
                       ("leftOnly", "a child that reaches past the send button's left edge alone: a scan"),
                       ("unseen", "an element added inside a tab the strip scrolls wholly out of view: a scan, since no part of that tab can be seen")):
            with self.subTest(k):
                self.assertIs(o[k]["scanned"], True, why)

    # Round 3 (2026-10-04, tests-1): the unchanged-value skip reads attribute records alone. An engine gives every childList record
    # attributeName null and oldValue null (Chromium's, probed by the round's refuter; the harness's records carry both, kids), and
    # getAttribute(null) is null, so a skip that dropped its type check would skip every childList record. Each kind of childList
    # record here reaches the watch and asks for its frame: a text written, an element removed, and an element added, which scans
    def test_the_unchanged_value_skip_never_skips_a_child_list_record(self):
        o = self._watch_fit(r"""
fire('romp:wsdown'); after(RHOLD_T);
const step = (fn) => { const reads = STYLE_READS, asks = ASKS; fn(); frame(); return { reads: STYLE_READS - reads, asks: ASKS - asks }; };
const shape = kids(footer, [], []);
const written = step(() => text(timer));
const removed = step(() => deliver(kids(footer, [], [timer])));
const addedEl = step(() => added(add(footer, [80, 764, 40, 16])));
out({ shape: [shape.attributeName, shape.oldValue], written, removed, addedEl, scan: scan() });""")
        self.assertEqual(o["shape"], [None, None], "the harness's childList records carry attributeName and oldValue null, as the engine's do")
        self.assertEqual(o["written"], {"reads": 1, "asks": 1}, "the status line's timer text written: one frame, a re-read (the skip read no attribute)")
        self.assertEqual(o["removed"], {"reads": 1, "asks": 1}, "an element removed from the footer: one frame, a re-read")
        self.assertEqual(o["addedEl"], {"reads": o["scan"], "asks": 1}, "an element added to the footer, which the scan does not hold: one frame, which scans")

    # Round 3 (2026-10-04, tests-2): rrec reads every node a childList record adds. An engine reports an innerHTML write or an
    # append(a, b) into a held control as ONE record carrying every node, and each held-control case above delivers one node per
    # record, so a watch that read only a record's first added node passed them. One record into the send button (a control the
    # scan holds) adds an icon inside its box and then a button far outside it: the frame scans and moves the badge below that
    # button. A record whose two nodes both lie inside the button re-reads, so the case cannot pass by scanning every record of two
    # nodes; and a record of a text node then an element into the footer, which the scan does not hold, scans (the loop's other
    # branch)
    def test_every_node_a_record_adds_is_read_not_only_the_first(self):
        o = self._watch_fit(r"""
fire('romp:wsdown'); after(RHOLD_T);
const rec = (target, nodes) => { const reads = STYLE_READS; deliver(kids(target, nodes, [])); frame(); const n = STYLE_READS - reads; return { reads: n, scanned: n === scan(), place: at() }; };
const bothIn = rec(send, [add(send, [340, 794, 20, 20]), add(send, [324, 788, 12, 12])]);
const inThenOut = rec(send, [add(send, [340, 794, 20, 20]), add(send, [240, 52, 140, 40], { position: 'absolute', sel: 'button' })]);
const textThenEl = rec(footer, [TEXT, add(footer, [80, 764, 40, 16])]);
out({ bothIn, inThenOut, textThenEl });""")
        at52 = {"top": "52px", "right": "8px", "painted": True}
        self.assertEqual(o["bothIn"], {"reads": 1, "scanned": False, "place": at52}, "two nodes in one record, both inside the send button's box: a re-read, no scan")
        with self.subTest("an icon, then a button outside"):
            self.assertEqual((o["inThenOut"]["scanned"], o["inThenOut"]["place"]), (True, {"top": "100px", "right": "8px", "painted": True}),
                             "an icon inside the button, then a button far outside it, in one record: a scan, which finds the second node's button and "
                             "moves the badge below it (52 + 40 + 8)")
        with self.subTest("a text node, then an element"):
            self.assertIs(o["textThenEl"]["scanned"], True, "a text node then an element in one record into the footer, which the scan does not hold: a scan")

    # Ruling 1 at 79dce614c (2026-10-04): on the desktop the chat writes the reply chips' hidden attribute at each scroll step, to the
    # value it had, and the chips (fixed, outside the list, holding elements, no control) are an element the watch must scan for when
    # an attribute changes, so the lab measured a scan of every element at each scroll step. Each attribute record now carries the
    # value it had (attributeOldValue), and a record whose old value is the value the element has now is skipped: it asks for no frame
    # and reads nothing. A record whose value did change scans as before, alone or beside an unchanged one in the same delivery.
    # The skip holds for each attribute the watch filters on and on each surface it observes: a class written to the value it had on
    # the chips, and a class, style and hidden attribute each written to the value it had on the list itself and on a sticky element
    # in it (the list and that element hold elements, so a changed write on either scans), ask for nothing too
    def test_an_attribute_written_to_the_value_it_had_asks_for_nothing_and_a_changed_one_scans(self):
        o = self._watch_fit(r"""
const chips = add(null, [200, 600, 190, 40], { position: 'fixed' }); chips.id = 'chips'; chips.attrs.hidden = '';   // the reply chips, hidden
add(chips, [210, 610, 80, 20]);
fire('romp:wsdown'); after(RHOLD_T);
const step = (fn) => { const reads = STYLE_READS, asks = ASKS; fn(); frame(); return { reads: STYLE_READS - reads, asks: ASKS - asks }; };
const unchanged = step(() => same(chips, 'hidden'));
const unchangedHeld = step(() => { field.attrs.style = 'height: 40px'; same(field, 'style'); });
const changedFirst = step(() => deliverAll([attrRec(chips, 'class', 'reply-chips'), sameRec(chips, 'hidden')]));
const changedLast = step(() => deliverAll([sameRec(chips, 'hidden'), attrRec(chips, 'class', 'reply-chips on')]));
const shown = step(() => attr(chips, 'hidden', null));
// each attribute present, then written again to the value it has (a classList.add of a class it holds, a style property set to its value)
CONTENT.attrs.class = 'list'; CONTENT.attrs.style = 'padding-top: 8px'; CONTENT.attrs.hidden = '';
head.attrs.class = 'sub-head'; head.attrs.style = 'top: 0px'; head.attrs.hidden = '';
// and then each written to a new value (hidden removed), which shows the record reaches the watch: a scan
const again = {}, then = {};
for (const [nm, el, a] of [['chips', chips, 'class'], ['list', CONTENT, 'class'], ['list', CONTENT, 'style'], ['list', CONTENT, 'hidden'],
                           ['sticky', head, 'class'], ['sticky', head, 'style'], ['sticky', head, 'hidden']]) {
  again[nm + ' ' + a] = step(() => same(el, a));
  then[nm + ' ' + a] = step(() => attr(el, a, a === 'hidden' ? null : el.attrs[a] + ' x'));
}
out({ unchanged, unchangedHeld, changedFirst, changedLast, shown, again, then, scan: scan() });""")
        self.assertEqual(o["unchanged"], {"reads": 0, "asks": 0},
                         "the chips' hidden attribute written to the value it had: skipped, no frame asked and no style read (79dce614c: a scan of every element)")
        self.assertEqual(o["unchangedHeld"], {"reads": 0, "asks": 0}, "the composer's style written to the value it had: skipped too, not even a re-read")
        for k in ("changedFirst", "changedLast"):
            self.assertEqual(o[k], {"reads": o["scan"], "asks": 1}, k + ": a changed class beside an unchanged hidden write in one delivery: one frame, which scans")
        self.assertEqual(o["shown"], {"reads": o["scan"], "asks": 1}, "the hidden attribute removed, a value that changed: one frame, which scans")
        self.assertEqual(sorted(o["again"]), sorted(["chips class", "list class", "list style", "list hidden", "sticky class", "sticky style", "sticky hidden"]),
                         "every surface and attribute was tried")
        for k, v in sorted(o["again"].items()):
            with self.subTest(k):
                self.assertEqual(v, {"reads": 0, "asks": 0}, k + " written to the value it had: skipped, no frame asked and no style read")
                self.assertEqual(o["then"][k], {"reads": o["scan"], "asks": 1}, k + " written to a new value next: one frame, which scans (the record reaches the watch)")

    # Round 3 (2026-10-04, extra5-1, disclosed): a scroll through a transcript that is not from today scans, because the chat moves its
    # day label (.rail-day, its style top) and shows or hides its sticky stamp (.time-marker.rail-sticky, its display) at the handoffs
    # between the rail's stamps: fixed elements outside the list that no scan holds, so each changed write asks for a scan (the build's
    # lab probe: ten wheel steps up gave the rail's writes 2 scans in Chromium and in Firefox and 4 to 8 in WebKit). The narrowing that
    # would spare them was declined, since a class or hidden write on such an element can show a control elsewhere through a sibling or
    # :has() selector, so the scans stand and the texts say so. The case runs the writes; the text check holds the kernel's comment and
    # the placement entry to naming them, which on its own proves nothing about behaviour
    def test_the_rail_writes_of_a_transcript_not_from_today_scan_and_the_texts_say_so(self):
        o = self._watch_fit(r"""
const day = add(null, [11, 41, 60, 14], { position: 'fixed' }); day.attrs.style = 'left: 11px; top: 41px';      // the day label
const stamp = add(null, [3, 50, 56, 14], { position: 'fixed' }); stamp.attrs.style = 'left: 3px; top: 50px';    // the sticky stamp
fire('romp:wsdown'); after(RHOLD_T);
const step = (fn) => { const reads = STYLE_READS, asks = ASKS; fn(); frame(); return { reads: STYLE_READS - reads, asks: ASKS - asks }; };
const moved = step(() => { day.box[1] = 88; attr(day, 'style', 'left: 11px; top: 88px'); });
const hidden = step(() => { stamp.cs.display = 'none'; attr(stamp, 'style', 'left: 3px; top: 50px; display: none'); });
const unchanged = step(() => same(day, 'style'));
out({ moved, hidden, unchanged, scan: scan() });""")
        self.assertEqual(o["moved"], {"reads": o["scan"], "asks": 1}, "the day label's top written to a new value: one frame, which scans")
        self.assertEqual(o["hidden"], {"reads": o["scan"], "asks": 1}, "the sticky stamp hidden by its style: one frame, which scans")
        self.assertEqual(o["unchanged"], {"reads": 0, "asks": 0}, "the day label's style written to the value it had: skipped")
        root = os.path.dirname(HERE)
        with open(os.path.join(root, "kernel", "kernel.py"), encoding="utf-8") as f:
            src = f.read()
        with open(os.path.join(root, "upstream", "2026-10-02-reconnect-badge-below-pane-header.md"), encoding="utf-8") as f:
            entry = f.read()
        for what, text in (("the kernel's comment", src[src.index("def _pane_spin"):src.index("def _chat_page")]), ("the placement entry", entry)):
            for name in (".rail-day", ".time-marker.rail-sticky", "not from today"):
                with self.subTest(what=what, name=name):
                    self.assertTrue(name in text, what + " names " + name + " among the changes that still scan (the case above runs them)")

    def test_a_change_that_can_add_a_control_scans_again(self):
        o = self._watch_fit(r"""
fire('romp:wsdown'); after(RHOLD_T);
let reads = STYLE_READS;
const sub = add(CONTENT, [0, 52, 390, 31], { position: 'sticky' }); sub.id = 'sub'; add(sub, [360, 58, 20, 20], { sel: '[role=button]' });
added(sub); frame(); const subHead = { place: at(), scanned: STYLE_READS - reads === scan() };
const pin2 = add(sub, [240, 58, 100, 20], { sel: 'button' }); reads = STYLE_READS; added(pin2); frame(); const inSub = { place: at(), scanned: STYLE_READS - reads === scan() };
const wrap = add(null, [200, 90, 190, 40]); const shown = add(wrap, [200, 90, 190, 40], { sel: 'button' }); shown.cs.visibility = 'hidden';
reads = STYLE_READS; added(wrap); frame(); const hiddenStill = at();
shown.cs.visibility = 'visible'; reads = STYLE_READS; attr(wrap, 'class'); frame(); const revealed = { place: at(), scanned: STYLE_READS - reads === scan() };
reads = STYLE_READS; attr(send, 'class'); frame(); const iconButton = STYLE_READS - reads === scan();
out({ subHead, inSub, hiddenStill, revealed, iconButton });""")
        self.assertEqual(o["subHead"], {"place": {"top": "52px", "right": "38px", "painted": True}, "scanned": True},
                         "a sticky header with a pin added as the list's own child: a scan, and the badge goes left of the pin (390 - 360 + 8)")
        self.assertEqual(o["inSub"], {"place": {"top": "86px", "right": "8px", "painted": True}, "scanned": True},
                         "a control added inside that header, which the scan it caused made the watch observe: a scan, and the badge goes below the "
                         "header's controls (58 + 20 + 8), as left of both would not fit")
        self.assertEqual(o["hiddenStill"], {"top": "86px", "right": "8px", "painted": True}, "a hidden control added outside the list: scanned, not counted")
        self.assertEqual(o["revealed"], {"place": {"top": "138px", "right": "8px", "painted": True}, "scanned": True},
                         "a class change on its wrapper, an element the scan did not hold, shows it: a scan, and the badge goes below it (90 + 40 + 8)")
        self.assertIs(o["iconButton"], True, "a class change on a control the scan holds that holds an element (its icon): a scan")

    # The list too short for the badge (the rehearsed check of round 1, 2026-10-03): with no clear place above the list's visible
    # bottom the search kept the first place, and a landscape phone with the keyboard up and a long pinned note left a list 20 px
    # tall, so the badge sat over the composer's buttons just below it. Now it takes the place in the pane's view, at the right
    # edge, 8 px above or below a control's edge, that covers the least of the controls, nearest the first place: a clear one
    # wherever the view has one.
    def test_a_list_shorter_than_the_badge_sends_it_above_the_controls_just_below_the_list(self):
        o = self._fit(r"""
shortList(179, 119); resize(99);                                      // the list runs from 99 to 119: a header and a long pinned note above it
add(null, [0, 0, 390, 45], { sel: 'button' });                        // the header's session picker, across the page
add(null, [250, 121, 60, 20], { sel: 'button' }); add(null, [320, 121, 60, 20], { sel: 'button' });   // the composer's two buttons, just below the list
add(null, [0, 121, 60, 20], { sel: 'button' });                       // its attach button at the left, level with them and outside the badge's column (248 to 382)
add(null, [40, 147, 300, 30], { sel: 'textarea' });                   // its text field
const atLoad = at();
fire('romp:wsdown'); after(RHOLD_T);
out({ atLoad, atPaint: at() });""")
        self.assertEqual(o["atLoad"], {"top": "107px", "right": "8px", "painted": False})
        self.assertEqual(o["atPaint"], {"top": "88px", "right": "8px", "painted": True},
                         "8 px above the composer's buttons (121 - 8 - 25), over the pinned note's text, which holds no control: the nearest clear place in "
                         "the view (below the header, at 53 px, is clear too but farther), not the first place at 107 px over the buttons; the attach "
                         "button beside the column counts for no place (weighed as a negative area it made 114 px, 8 px above the text field and over "
                         "the buttons, look best)")

    def test_with_the_view_above_the_list_taken_the_badge_goes_below_the_controls_under_it(self):
        o = self._fit(r"""
shortList(260, 119); resize(99);
add(null, [0, 0, 390, 45], { sel: 'button' });                        // the header
add(null, [300, 60, 85, 39], { sel: 'button' });                      // a control at the pinned note's right end, just above the list
add(null, [250, 121, 60, 20], { sel: 'button' }); add(null, [320, 121, 60, 20], { sel: 'button' });   // the composer's buttons, just below the list
add(null, [40, 200, 300, 40], { sel: 'textarea' });                   // its text field, lower down
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
        self.assertEqual(o["atPaint"], {"top": "149px", "right": "8px", "painted": True},
                         "8 px below the composer's buttons (121 + 20 + 8), clear of everything: every place above them covers a control, and the clear "
                         "place above the text field (167 px) is farther")

    def test_with_no_clear_place_in_the_view_the_badge_takes_the_place_that_covers_the_least(self):
        o = self._fit(r"""
shortList(179, 119); resize(99);
add(null, [0, 0, 390, 95], { cursor: 'pointer' });                    // a control across the chrome above the list, to 4 px above its top
add(null, [0, 125, 390, 54], { sel: 'textarea' });                    // the composer's text field across the page, from 6 px below the list
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
        self.assertEqual(o["atPaint"], {"top": "103px", "right": "8px", "painted": True},
                         "8 px below the chrome's control: 3 rows over the text field, against 7 at the first place (107 px); 8 px above the text field "
                         "(92 px) covers 3 rows of the chrome's control too but is farther; nothing off the view is taken")

    def test_with_no_clear_place_the_first_place_stays_when_it_covers_the_least(self):
        # the first place is one of the places weighed, so the fallback never moves the badge onto more of a control than it covered
        o = self._fit(r"""
shortList(179, 119); resize(99);
add(null, [0, 0, 390, 103], { cursor: 'pointer' });                   // a control across the chrome, drawn 4 px over the list's top from outside it
add(null, [0, 130, 390, 49], { sel: 'textarea' });                    // the composer's text field across the page, from 11 px below the list
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
        self.assertEqual(o["atPaint"], {"top": "107px", "right": "8px", "painted": True},
                         "the first place covers 2 rows of the text field; 8 px below the chrome's control (111 px) covers 6 rows of the text field, and 8 px "
                         "above the text field (97 px) 6 rows of the chrome's control")

    def test_with_every_place_equally_covered_the_badge_keeps_its_first_place(self):
        o = self._fit(r"""
add(null, [0, 0, 390, 844], { cursor: 'pointer' });                  // a control over the whole page
fire('romp:wsdown'); after(RHOLD_T);
out({ atPaint: at() });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True}, "every place in the view covers the control whole: the first place, not off the page")

    def test_the_search_runs_only_while_the_badge_is_painted(self):
        o = self._fit(r"""
const head = add(CONTENT, [0, 52, 390, 31], { position: 'sticky' }); add(head, [360, 58, 20, 20], { sel: '[role=button]' });
let reads = STYLE_READS; resize(44); const unpainted = { reads: STYLE_READS - reads, top: topOf() };
fire('romp:wsdown'); after(RHOLD_T); const painted1 = at();
fire('romp:wsfresh'); reads = STYLE_READS; resize(44); const after1 = { reads: STYLE_READS - reads, top: topOf() };
out({ unpainted, painted1, after1 });""")
        self.assertEqual(o["unpainted"], {"reads": 1, "top": "52px"}, "a resize event on a healthy page reads the list's own style alone (the scroll-area test) and writes the first place")
        self.assertEqual(o["painted1"], {"top": "52px", "right": "38px", "painted": True}, "painted, the search moves it left of the header's pin")
        self.assertEqual(o["after1"], {"reads": 1, "top": "52px"}, "after the fresh frame the badge is down, and the next resize event goes back to the first place without a search")

    def test_an_auto_overflow_list_counts_as_a_scroll_area(self):
        # the Outline's, the Feed's and the Waiting pane's lists are overflow-y:auto; the chat's transcript is scroll
        o = self._run(r"""
out({ top: BADGE.style.top, observers: ROS.length });""", pre=self._PLACE_PRE.replace("COVER = 'scroll'", "COVER = 'auto'"))
        self.assertEqual(o, {"top": "52px", "observers": 1, "textWrites": []})

    def test_the_fork_lines_sit_around_upstreams_badge_lines_which_stay_byte_for_byte(self):
        js = km._pane_spin("content", "live-ask")
        up_badge = "function badge(on){if(rb)rb.classList.toggle('on',!!on);clearTimeout(bfail);if(on)bfail=setTimeout(function(){badge(false);},30000);}"
        up_down = "window.addEventListener('romp:wsdown',function(){if(ready()){badge(true);}else{show();}});"
        up_fresh = "window.addEventListener('romp:wsfresh',function(){badge(false);});})();"
        for line in (up_badge, up_down, up_fresh):
            self.assertEqual(js.count(line), 1, line)
        before = "window.addEventListener('romp:wsdown',function(){ron=!!(rb&&rb.classList.contains('on'));});"
        afterl = "window.addEventListener('romp:wsdown',function(){if(!rb||!rb.classList.contains('on'))return;if(ron){rfail();return;}"
        self.assertLess(js.index(up_badge), js.index(before), "the fork's state reads bfail and rb, declared on upstream's lines")
        self.assertLess(js.index(before), js.index(up_down), "the recording listener runs before upstream's wsdown line (registration order)")
        self.assertLess(js.index(up_down), js.index(afterl), "the hold's listener runs after it, so it sees the badge upstream raised")
        self.assertLess(js.index(afterl), js.index(up_fresh), "inserted before upstream's last line")


if __name__ == "__main__":
    unittest.main()
