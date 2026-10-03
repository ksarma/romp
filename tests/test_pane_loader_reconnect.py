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
// observer's callback, target and state so the fit cases can deliver a change to the page as the engine would
const MOS = [];
global.MutationObserver = class { constructor(cb) { this.cb = cb; this.on = false; MOS.push(this); } observe(t, o) { this.on = true; this.target = t; this.opts = o; } disconnect() { this.on = false; } };
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

    # The badge's place (finding of 2026-10-02): 8 px below the top of the pane's content container when that container is the
    # pane's scroll area (every pane page: a header over a scrolling list), so it covers none of the header's controls (upstream's
    # top:8px hid the phone chat's tag filter and + button, the desktop strip's tag filter and gear, and the phone Outline's tag
    # filter and search). The served legs measure the real geometry (_badge_clear_of_chrome); these cases run the logic in node.
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
    # a control outside the list, or a sticky or fixed element in the list that is or holds a control, whole (rfit, robs). These
    # cases run the search over a page of fake elements: each has a box, a computed style, a parent, and answers matches() for the
    # one selector entry it carries (so the product's RCTL list must name it) or its cursor. The served legs measure real engines.
    _FIT_PRE = r"""
document.documentElement = { id: 'html', clientWidth: 390, clientHeight: 844 };
const ALL = [CONTENT];                                                // the body's elements in document order
document.body = { getElementsByTagName: (t) => (t === '*' ? ALL : []) };
let STYLE_READS = 0;
global.getComputedStyle = (el) => { STYLE_READS++; return el === CONTENT ? { overflowY: COVER, position: 'static', cursor: 'auto', visibility: 'visible', display: 'block' } : el.cs; };
const inside = (anc, n) => { for (let e = n; e; e = e.parent) if (e === anc) return true; return false; };
CONTENT.contains = (n) => inside(CONTENT, n);
// add(parent, box [left, top, width, height], { position, cursor, sel }): an element under `parent` (null: the body, outside the list)
const add = (parent, box, o) => { const e = { parent, box: box.slice(), sel: (o && o.sel) || '',
  cs: { position: (o && o.position) || 'static', cursor: (o && o.cursor) || 'auto', visibility: 'visible', display: 'block', overflowY: 'visible' },
  getBoundingClientRect() { const [l, t, w, h] = this.box; return { left: l, top: t, right: l + w, bottom: t + h, width: w, height: h }; },
  contains(n) { return inside(this, n); }, matches(list) { return !!this.sel && list.split(',').indexOf(this.sel) >= 0; } };
  const at = parent ? ALL.lastIndexOf(ALL.filter((x) => inside(parent, x)).pop()) + 1 : ALL.length; ALL.splice(at, 0, e); return e; };
const rightOf = () => (BADGE.style.right ? BADGE.style.right : '8px');
const at = () => ({ top: topOf(), right: rightOf(), painted: painted() });
const mo = () => MOS.filter((m) => m.on && m.target === document.body).length;   // the badge's watch (the sheet's own observer watches the list)
const change = (target) => task(() => MOS.filter((m) => m.on && m.target === document.body).forEach((m) => m.cb([{ type: 'childList', target }])));
const scroll = () => task(() => (DOCL.scroll || []).slice().forEach((f) => f({ type: 'scroll' })));
// a short view and a short list (a landscape phone with the keyboard up): the page's height and the list's bottom
const shortList = (viewH, bottom) => { document.documentElement.clientHeight = viewH; CONTENT.getBoundingClientRect = () => ({ top: CTOP, left: 0, right: 390, bottom }); };
"""

    def _fit(self, scenario):
        return self._run(scenario, pre=self._PLACE_PRE + self._FIT_PRE)

    def test_a_painted_badge_goes_below_a_sticky_header_in_the_list_that_holds_a_control(self):
        # the subagent viewer: a sticky line at the list's top (#sub-head, 8 px down) with its pin, a role=button, at the right end
        o = self._fit(r"""
const head = add(CONTENT, [0, 52, 390, 31], { position: 'sticky' });
add(head, [360, 58, 20, 20], { sel: '[role=button]' });
const atLoad = at();
fire('romp:wsdown'); after(RHOLD_T); const atPaint = at();
out({ atLoad, atPaint, watching: mo() });""")
        self.assertEqual(o["atLoad"], {"top": "52px", "right": "8px", "painted": False}, "unpainted, the first place: no search on a healthy page")
        self.assertEqual(o["atPaint"], {"top": "91px", "right": "8px", "painted": True}, "painted below the header (52 + 31 + 8), not on it")
        self.assertEqual(o["watching"], 1, "and watching the page for what could move it")

    def test_a_control_drawn_over_the_list_from_outside_it_moves_the_badge_below_it_when_it_appears(self):
        # the landing notice: outside the list, drawn over its top, a pointer cursor and nothing else, shown after the paint
        o = self._fit(r"""
fire('romp:wsdown'); after(RHOLD_T); const atPaint = at();
const notice = add(null, [42, 54, 307, 29], { cursor: 'pointer' });
change(BADGE); const ownChange = at();                                 // a change to the badge alone (its own place written) moves nothing
change(notice); const shown = at();
out({ atPaint, ownChange, shown });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True})
        self.assertEqual(o["ownChange"], {"top": "52px", "right": "8px", "painted": True}, "the badge's own mutations are not a change to the page")
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
        # chip that has a grab cursor and nothing else; the badge's first place (8 px) is on the second and third heads
        o = self._fit(r"""
resize(0);
for (const [l, w] of [[12, 120], [140, 120], [268, 110]]) { const h = add(CONTENT, [l, 12, w, 29], { position: 'sticky' }); add(h, [l + 2, 14, 68, 20], { cursor: 'grab' }); }
const atLoad = at();
fire('romp:wsdown'); after(RHOLD_T);
out({ atLoad, atPaint: at() });""")
        self.assertEqual(o["atLoad"], {"top": "8px", "right": "8px", "painted": False})
        self.assertEqual(o["atPaint"], {"top": "49px", "right": "8px", "painted": True}, "below the heads' row (12 + 29 + 8): left of them would not fit")

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
const head = add(CONTENT, [0, 300, 390, 29], { position: 'sticky' }); add(head, [10, 304, 60, 20], { sel: 'button' });
fire('romp:wsdown'); after(RHOLD_T); const atPaint = at();
head.box[1] = 60; ALL[2].box[1] = 64;                                 // the list scrolls: the header comes up under the badge
scroll(); const scrolled = at();
const reads = STYLE_READS; scroll(); const rereads = STYLE_READS - reads;
fire('romp:wsfresh'); const cleared = { painted: painted(), watching: mo(), scrollListeners: (DOCL.scroll || []).length };
change(head); const afterChange = { watching: mo(), scrollListeners: (DOCL.scroll || []).length };
out({ atPaint, scrolled, rereads, cleared, afterChange });""")
        self.assertEqual(o["atPaint"], {"top": "52px", "right": "8px", "painted": True})
        self.assertEqual(o["scrolled"], {"top": "97px", "right": "8px", "painted": True}, "the scroll moves it below the header (60 + 29 + 8)")
        self.assertLessEqual(o["rereads"], 1, "a scroll re-reads the boxes the last scan found; it does not scan the page's styles again")
        self.assertIs(o["cleared"]["painted"], False)
        self.assertEqual(o["afterChange"], {"watching": 0, "scrollListeners": 0}, "with the badge down, the next change ends the watch: no observer, no scroll listener")

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
fire('romp:wsdown'); after(RHOLD_T); const painted1 = topOf();
fire('romp:wsfresh'); reads = STYLE_READS; resize(44); const after1 = { reads: STYLE_READS - reads, top: topOf() };
out({ unpainted, painted1, after1 });""")
        self.assertEqual(o["unpainted"], {"reads": 1, "top": "52px"}, "a resize event on a healthy page reads the list's own style alone (the scroll-area test) and writes the first place")
        self.assertEqual(o["painted1"], "91px")
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
