"""The dashboard reloads ITSELF on a kernel restart and on a newer served bundle (T265).

The user's ruling of 2026-09-08 supersedes their 2026-07-13 preference for a banner the reader clicks. The reload
core (kernel.py _RELOAD_CORE_JS, window.__rompReload on every kernel-served page) runs here for REAL: node executes
the IIFE between its anchors with fakes for document, window, location, sessionStorage and fetch, one process per
scenario (the core installs once per window), and the scenario reads its state back by name. Pinned alongside:
the wiring (the shim's raise, the shim's reconnect, the shell's socket, the stale banner's poll and fallback, the
pages that embed the core) and the remote exclusion (federation drops remote keepalives, so a REMOTE kernel's
restart or bundle never reaches the core). Synthetic values only."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
km = load_source("romp_kernel_autoreload", os.path.join(BIN, "romp-kernel"))

# The browser the core thinks it runs in. `var` at module scope shadows node's globals; the core's own
# `document.addEventListener` calls land in LISTENERS so a scenario can emit the gesture events by name.
HARNESS = r"""
var LISTENERS = {}, STORE = {}, REMOVED = [], FETCHES = [], RELOADS = 0, REFUSE = false, PERSISTED = 0, WLISTENERS = {};
var SEL = { rangeCount: 0, isCollapsed: true, toString: function () { return ""; } };
var COMPOSER = { tagName: "TEXTAREA", value: "" };              // the chat composer, one editable among any
var FOCUSED = true;                                             // document.hasFocus()
var IFRAMES = [];
var document = {
  addEventListener: function (t, f) { (LISTENERS[t] = LISTENERS[t] || []).push(f); },
  getSelection: function () { return SEL; },
  hasFocus: function () { return FOCUSED; },
  getElementById: function (id) { return id === "composer-input" ? COMPOSER : null; },
  activeElement: null,
  body: { classList: { remove: function () { REMOVED.push(Array.prototype.slice.call(arguments)); } } },
  querySelectorAll: function () { return IFRAMES; }
};
var window = { addEventListener: function (t, f) { (WLISTENERS[t] = WLISTENERS[t] || []).push(f); } };
window.parent = window;
window.__rompPersistForReload = function () { PERSISTED++; };
var location = { pathname: "/", reload: function () { RELOADS++; if (REFUSE) throw new Error("host forbids reload"); } };
var sessionStorage = {
  setItem: function (k, v) { STORE[k] = v; }, getItem: function (k) { return k in STORE ? STORE[k] : null; },
  removeItem: function (k) { delete STORE[k]; }
};
var VERSION = null;
function fetch(u) { FETCHES.push(u); return Promise.resolve({ json: function () { return Promise.resolve(VERSION); } }); }
function emit(t) { (LISTENERS[t] || []).forEach(function (f) { f({}); }); }
function wemit(t) { (WLISTENERS[t] || []).forEach(function (f) { f({}); }); }
function tick() { return new Promise(function (r) { setTimeout(r, 0); }); }
function state() {
  var R = window.__rompReload;
  return { reloads: RELOADS, fired: R.fired(), owed: R.owed(), waiting: R.waiting, persisted: PERSISTED, removed: REMOVED, refusedFor: R.refusedFor(),
           released: R.released(), stored: STORE["romp:reloaded"] ? JSON.parse(STORE["romp:reloaded"]) : null, fetches: FETCHES.length };
}
function out(o) { process.stdout.write("RESULT:" + JSON.stringify(o) + "\n"); }
"""


def run_core(scenario, v=7, boot="1.1"):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed")
    d = tempfile.mkdtemp(prefix="reload-core-")
    path = os.path.join(d, "core.js")
    with open(path, "w") as f:
        f.write(HARNESS + km._reload_core_js(v, boot) + "\n(async function(){\n" + scenario + "\n})();\n")
    r = subprocess.run([node, path], capture_output=True, text=True, timeout=60)
    shutil.rmtree(d, ignore_errors=True)
    if r.returncode != 0:
        raise AssertionError("node failed:\n" + r.stderr)
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("RESULT:")), None)
    assert line, "no RESULT line:\n" + r.stdout
    return json.loads(line[len("RESULT:"):])


class ReloadCoreExecuted(unittest.TestCase):
    def test_a_newer_dv_reloads_at_once_when_idle_and_persists_first(self):
        s = run_core("""
var R = window.__rompReload;
R.noteDv(7); var same = state();          // the page's own build
R.noteDv(5); var older = state();         // an OLDER token (a rolled-back peer) is not drift
R.noteDv(8);
out({ same: same, older: older, after: state() });""")
        self.assertEqual(s["same"]["reloads"], 0)
        self.assertEqual(s["older"]["reloads"], 0)
        a = s["after"]
        self.assertEqual(a["reloads"], 1)
        self.assertTrue(a["fired"])
        self.assertEqual(a["stored"]["reason"], "build")
        self.assertEqual(a["stored"]["detail"], "8")
        self.assertEqual(a["stored"]["from"], 7)
        self.assertEqual(a["stored"]["path"], "/", "the marker names the page that reloaded")
        self.assertEqual(a["persisted"], 1, "the pane's persist hook ran before the reload")
        self.assertIn(["settings-open", "picker-open"], a["removed"], "the lifted modals close")

    def test_a_restart_is_a_reopen_against_a_new_boot_id_never_a_blip(self):
        s = run_core("""
var R = window.__rompReload;
VERSION = { boot: "1.1", dist_ver: 7 }; R.checkBoot(); await tick(); await tick(); var blip = state();
VERSION = { boot: "2.2", dist_ver: 7 }; R.checkBoot(); await tick(); await tick();
out({ blip: blip, after: state() });""")
        self.assertEqual(s["blip"]["reloads"], 0, "the same kernel answered: a socket blip, not a restart")
        self.assertEqual(s["blip"]["fetches"], 1)
        self.assertEqual(s["after"]["reloads"], 1)
        self.assertEqual(s["after"]["stored"]["reason"], "restart")
        self.assertEqual(s["after"]["stored"]["detail"], "2.2")

    def test_version_readings_feed_both_signals(self):
        s = run_core("""
var R = window.__rompReload;
R.noteVersion({ boot: "1.1", dist_ver: 7 }); var quiet = state();
R.noteVersion({ boot: "1.1", dist_ver: 9 });
out({ quiet: quiet, after: state() });""")
        self.assertEqual(s["quiet"]["reloads"], 0)
        self.assertEqual(s["after"]["stored"]["reason"], "build")

    def test_a_held_pointer_arms_and_the_pointerup_fires(self):
        s = run_core("""
var R = window.__rompReload;
emit("pointerdown");
R.noteDv(8); var held = state();
emit("pointerup"); var atOnce = state(); await tick();
out({ held: held, atOnce: atOnce, after: state() });""")
        self.assertEqual(s["held"]["reloads"], 0)
        self.assertEqual(s["held"]["waiting"], "pointer")
        self.assertEqual(s["held"]["owed"]["reason"], "build", "armed, not dropped")
        self.assertEqual(s["atOnce"]["reloads"], 0, "the fire waits one tick so the click the same press produces lands on its control first")
        self.assertEqual(s["after"]["reloads"], 1)

    def test_a_drag_in_flight_arms_and_dragend_fires(self):
        s = run_core("""
var R = window.__rompReload;
emit("dragstart"); R.noteDv(8); var held = state(); emit("dragend"); await tick();
out({ held: held, after: state() });""")
        self.assertEqual(s["held"]["waiting"], "drag")
        self.assertEqual(s["held"]["reloads"], 0)
        self.assertEqual(s["after"]["reloads"], 1)

    def test_a_selection_being_made_arms_and_its_collapse_fires(self):
        s = run_core("""
var R = window.__rompReload;
SEL = { rangeCount: 1, isCollapsed: false, toString: function () { return "some words"; } };
R.noteDv(8); var held = state();
SEL = { rangeCount: 1, isCollapsed: true, toString: function () { return ""; } }; emit("selectionchange"); await tick();
out({ held: held, after: state() });""")
        self.assertEqual(s["held"]["waiting"], "selection")
        self.assertEqual(s["held"]["reloads"], 0)
        self.assertEqual(s["after"]["reloads"], 1)

    def test_a_composer_with_text_and_focus_arms_and_emptying_or_blurring_fires(self):
        s = run_core("""
var R = window.__rompReload;
document.activeElement = COMPOSER; COMPOSER.value = "half a thought";
R.noteDv(8); var held = state();
COMPOSER.value = "half a thought, more"; emit("input"); await tick(); var typing = state();
COMPOSER.value = ""; emit("input"); await tick();
out({ held: held, typing: typing, after: state() });""")
        self.assertEqual(s["held"]["waiting"], "typing")
        self.assertEqual(s["typing"]["reloads"], 0, "typing keeps the hold")
        self.assertEqual(s["after"]["reloads"], 1, "an emptied composer releases it")
        s2 = run_core("""
var R = window.__rompReload;
document.activeElement = COMPOSER; COMPOSER.value = "draft"; R.noteDv(8);
document.activeElement = null; emit("focusout"); await tick();
out({ after: state() });""")
        self.assertEqual(s2["after"]["reloads"], 1, "a blurred composer releases it (the draft is persisted already)")

    def test_a_window_blur_releases_every_hold(self):
        s = run_core("""
var R = window.__rompReload;
emit("pointerdown"); emit("dragstart"); R.noteDv(8); var held = state(); wemit("blur"); await tick();
out({ held: held, after: state() });""")
        self.assertEqual(s["held"]["reloads"], 0)
        self.assertEqual(s["after"]["reloads"], 1)

    def test_a_refused_reload_falls_back_to_the_banner_hook(self):
        s = run_core("""
var R = window.__rompReload; var refused = [];
R.refused = function (o) { refused.push(o); }; REFUSE = true;
R.noteDv(8); var first = state();
emit("pointerup"); await tick(); emit("selectionchange"); await tick(); R.noteVersion({ boot: "1.1", dist_ver: 8 }); var again = state(); var shownAfterAgain = refused.length;
R.noteDv(9); var newer = state();
out({ refused: refused, first: first, again: again, shownAfterAgain: shownAfterAgain, newer: newer });""")
        f = s["first"]
        self.assertEqual(f["reloads"], 1, "the reload was attempted")
        self.assertFalse(f["fired"], "…and stood down when the host threw")
        self.assertEqual(f["waiting"], "refused")
        self.assertEqual(f["refusedFor"], "build:8", "the refusal latches for this build")
        self.assertEqual(f["stored"], None, "no marker and no un-lifted modal for a reload that never happened")
        self.assertEqual(f["removed"], [])
        self.assertEqual(s["refused"][0], {"reason": "build", "detail": "8"})
        self.assertEqual(s["again"]["reloads"], 1, "gesture ends and the poll do not re-attempt the refused build")
        self.assertEqual(s["shownAfterAgain"], 1, "the banner is shown once for that build")
        self.assertEqual(s["newer"]["reloads"], 2, "a strictly newer build re-arms and tries again (and is refused again on this host)")
        self.assertEqual(len(s["refused"]), 2)

    def test_the_fresh_page_announces_once_from_the_marker(self):
        s = run_core("""
var R = window.__rompReload; var notes = [];
STORE["romp:reloaded"] = JSON.stringify({ reason: "restart", detail: "2.2", from: 6, t: 1 });
var first = R.announce(function (k, t) { notes.push([k, t]); });
var second = R.announce(function (k, t) { notes.push([k, t]); });
out({ first: first, second: second, notes: notes, left: STORE["romp:reloaded"] || null });""")
        self.assertEqual(s["first"], "Reloaded onto build 7 — the kernel restarted.")
        self.assertEqual(s["notes"], [["reload", "Reloaded onto build 7 — the kernel restarted."]])
        self.assertIsNone(s["second"], "one line per reload")
        self.assertIsNone(s["left"], "the marker is consumed")
        s2 = run_core("""
var R = window.__rompReload;
STORE["romp:reloaded"] = JSON.stringify({ reason: "build", detail: "9", from: 6, t: 1 });
out({ first: R.announce(null) });""")
        self.assertEqual(s2["first"], "Reloaded onto build 7 — a newer romp build was served.")
        s3 = run_core("""
var R = window.__rompReload;
STORE["romp:reloaded"] = JSON.stringify({ reason: "build", detail: "9", from: 6, path: "/feed", t: 1 });
out({ first: R.announce(null), left: STORE["romp:reloaded"] || null });""")
        self.assertIsNone(s3["first"], "a marker another page wrote (a standalone /feed reload) is not this page's to announce")
        self.assertIsNotNone(s3["left"], "…and it is LEFT for the page it names (T272, 2026-09-08): sessionStorage is shared across the shell "
                                         "and its same-origin panes, and a pane's shim that read as standalone for a beat consumed the "
                                         "shell's marker before the path check — the shell then found nothing to announce, and the "
                                         "notification-center line the served test waits for never appeared")
        # the shell's marker (path "/") survives a pane's early announce and is announced by the shell itself, once
        s4 = run_core("""
var R = window.__rompReload; var notes = [];
STORE["romp:reloaded"] = JSON.stringify({ reason: "restart", detail: "2.2", from: 6, path: "/", t: 1 });
location.pathname = "/chat"; var pane = R.announce(null);
location.pathname = "/"; var shell = R.announce(function (k, t) { notes.push([k, t]); }); var again = R.announce(null);
out({ pane: pane, shell: shell, again: again, notes: notes, left: STORE["romp:reloaded"] || null });""")
        self.assertIsNone(s4["pane"], "the chat pane leaves the shell's marker alone")
        self.assertEqual(s4["shell"], "Reloaded onto build 7 — the kernel restarted.", "the shell announces its own reload")
        self.assertEqual(s4["notes"], [["reload", "Reloaded onto build 7 — the kernel restarted."]])
        self.assertIsNone(s4["again"], "one line per reload"); self.assertIsNone(s4["left"], "consumed by its own page")

    def test_the_shell_composes_gesture_state_across_its_panes_and_a_pane_forwards_its_request(self):
        s = run_core("""
var R = window.__rompReload;
var paneBusy = "pointer";
var pane = { __rompReload: { busyHere: function () { return paneBusy; } }, __rompPersistForReload: function () { PERSISTED += 10; } };
IFRAMES = [{ contentWindow: pane }];
R.request("build", "8"); var held = state();
paneBusy = ""; R.tryFire();            // the pane's ending event calls the shell's tryFire
out({ held: held, after: state() });""")
        self.assertEqual(s["held"]["reloads"], 0)
        self.assertEqual(s["held"]["waiting"], "pointer", "a pane's held pointer holds the shell's reload")
        self.assertEqual(s["after"]["reloads"], 1)
        self.assertEqual(s["after"]["persisted"], 11, "the shell and every pane persisted before the reload")
        # a pane under a same-origin shell forwards: its own core never fires
        s2 = run_core("""
var shellReqs = [];
window.parent = { __rompReload: { request: function (r, d) { shellReqs.push([r, d]); }, tryFire: function () { shellReqs.push(["tryFire"]); } } };
var R = window.__rompReload;
R.noteDv(8); emit("pointerup"); await tick();
out({ shellReqs: shellReqs, inShell: R.inShell(), after: state() });""")
        self.assertTrue(s2["inShell"])
        self.assertEqual(s2["shellReqs"], [["build", "8"], ["tryFire"]])
        self.assertEqual(s2["after"]["reloads"], 0, "the top document reloads, never the pane alone")

    def test_a_panes_queued_sends_hold_the_reload_until_its_flush(self):
        s = run_core("""
var R = window.__rompReload; var queued = 1;
window.__rompPaneBusy = function () { return queued ? "sends" : ""; };   // the shim: everConnected && queue.length > queuedDiag
R.noteVersion({ boot: "2.2" }); var held = state();
queued = 0; R.ended(); await tick();                                    // the shim's ws.onopen flush
out({ held: held, after: state() });""")
        self.assertEqual(s["held"]["reloads"], 0, "a prompt typed during the outage sits in the pane's queue: the shell's earlier reopen must not take the page down")
        self.assertEqual(s["held"]["waiting"], "sends")
        self.assertEqual(s["after"]["reloads"], 1, "the flush is the ending event")

    def test_a_held_reload_wears_a_face_once_per_hold_and_never_for_a_gesture(self):
        # T272 follow-up (the manager's review): nothing displayed the core's `waiting`, so a reload held by a pane's
        # reason (an upload in flight) sat invisible. The `held` hook fires once per owed request and reason — the shell
        # files a notification-center line, a standalone pane raises its bar — and never for a momentary gesture hold.
        s = run_core("""
var R = window.__rompReload; var held = []; R.held = function (b, o) { held.push([b, o && o.reason]); };
var busyReason = "upload";
window.__rompPaneBusy = function () { return busyReason; };
R.noteVersion({ boot: "2.2" });                       // owed, held on the pane's upload
R.ended(); await tick(); R.ended(); await tick();     // re-asks while the same hold stands: no second line
busyReason = "held-send"; R.ended(); await tick();    // the reason changed: one line for it
busyReason = ""; R.ended(); await tick();             // idle: fires
out({ held: held, reloads: RELOADS, waiting: R.waiting });""")
        self.assertEqual(s["held"], [["upload", "restart"], ["held-send", "restart"]], "once per hold reason, with the owed request")
        self.assertEqual(s["reloads"], 1)
        s2 = run_core("""
var R = window.__rompReload; var held = []; R.held = function (b) { held.push(b); };
emit("pointerdown"); R.noteVersion({ boot: "2.2" });   // a held pointer: a gesture hold, no line
var during = state();
emit("pointerup"); await tick();
out({ held: held, during: during, reloads: RELOADS });""")
        self.assertEqual(s2["during"]["waiting"], "pointer")
        self.assertEqual(s2["held"], ["pointer"], "the hook is told every hold; the shell's line filters gestures out (heldReloadText)")
        self.assertEqual(s2["reloads"], 1)

    def test_a_touch_pan_holds_from_pointercancel_until_the_finger_lifts(self):
        s = run_core("""
var R = window.__rompReload;
emit("pointerdown"); emit("pointercancel");       // the touch became a scroll: the browser cancels the pointer, the finger is still down
R.noteDv(8); var panning = state();
emit("pointerup"); await tick(); var stillPanning = state();   // no pointerup comes for a cancelled pointer, but even one must not release the pan
emit("touchend"); await tick();
out({ panning: panning, stillPanning: stillPanning, after: state() });""")
        self.assertEqual(s["panning"]["reloads"], 0)
        self.assertEqual(s["panning"]["waiting"], "pan")
        self.assertEqual(s["stillPanning"]["reloads"], 0)
        self.assertEqual(s["after"]["reloads"], 1, "touchend releases the pan")

    def test_a_selection_counts_only_in_the_focused_document(self):
        s = run_core("""
var R = window.__rompReload;
SEL = { rangeCount: 1, isCollapsed: false, toString: function () { return "an old highlight"; } };
FOCUSED = false; R.noteDv(8);
out({ after: state() });""")
        self.assertEqual(s["after"]["reloads"], 1, "a highlight left in a pane the user is not in is not a gesture being made")

    def test_typing_in_any_editable_holds_not_only_the_composer(self):
        s = run_core("""
var R = window.__rompReload;
var pickerInput = { tagName: "INPUT", type: "text", value: "new-sess" };
document.activeElement = pickerInput; R.noteDv(8); var held = state();
var sel = { tagName: "SELECT", value: "x" }; document.activeElement = sel; emit("focusout"); await tick();
out({ held: held, after: state() });""")
        self.assertEqual(s["held"]["waiting"], "typing", "the new-session picker's name box holds like the composer")
        self.assertEqual(s["held"]["reloads"], 0)
        self.assertEqual(s["after"]["reloads"], 1, "a focused <select> is not text entry")

    def test_a_foreign_parent_leaves_the_pane_to_reload_itself(self):
        s = run_core("""
Object.defineProperty(window, "parent", { get: function () { throw new Error("cross-origin"); } });
var R = window.__rompReload; R.noteDv(8);
out({ inShell: R.inShell(), after: state() });""")
        self.assertFalse(s["inShell"])
        self.assertEqual(s["after"]["reloads"], 1, "an iframe in another app reloads itself")


class UploadHoldExecuted(unittest.TestCase):
    """The chat pane's hold for a file still shipping (T272, upstream #1123) and the fork's deadline behind it. render.ts
    wraps the shim's window.__rompPaneBusy and answers 'upload' while a ship awaits its ack and 'held-send' while the
    ship gate holds a send, and calls __rompReload.ended() when the last ack lands or the gate clears, so the hold ends
    on its own event like every gesture hold. The core defers a reload it owes while the pane's word is up, holds a
    shell's reload from a pane, and fires when the ending event lands and nothing else holds. The fork's own fold-4
    route to the same end (window.__rompReloadHold read as a 'ships' hold, re-checked on a 500 ms timer) was
    superseded by this one at the 2026-09-09 fold; its DEADLINE stays, re-expressed inside upstream's shape as the
    backstop the fold's ruling asked for (romp-general, 2026-09-09): a pane word that has blocked an owed reload
    for 60 s is released, one console line names the word and the seconds, and the reload fires with a note the
    pane's pre-reload hook reads through released() and persists among the toasts the fresh page replays. The
    clock is the pane word's, and a gesture anywhere leaves it alone, the word's own pane included (the fold's review,
    UI-2, and the verification that found the own-pane gap): busy() reads each window's gesture (busyHere) and its
    pane word (paneHere, the window's __rompPaneBusy alone) apart, so the word is seen behind a gesture in the shell,
    a sibling pane or the pane that owns it; the clock starts when the word first blocks an owed reload, gesture or
    not, runs while the same word stays up, and zeroes when the word drops to nothing or another clocked word replaces
    it, so a hold released and re-raised gets its own 60 s (the fold-4 review's F1) and a user's clicks, drags,
    selections and typing during a wedged upload, in that pane or any other, never restart its 60 s; past the
    deadline a gesture defers the release to its own ending event, and the first tryFire with nothing deferring fires
    at once. A gesture anywhere outranks every pane word for the word reported (K1) and has no deadline; the shim's
    'sends' (a prompt queued for a socket that is down) has no deadline either (NOCLOCK; the fold's review, F1/UI-1),
    since a reload over it would land on a kernel not answering the page and lose the prompt: it is reported ahead of
    a clocked word and defers a release past the deadline like a gesture, so a chat pane's upload beside a sibling
    pane's 'sends' clocks from its first sight and is released only when the flush ends the 'sends'. An older pane
    core without paneHere is read through its busyHere word. A refused reload with a release note pending persists once more without the release
    note (the fold's review, F2).
    The timers, the clock and the console are the scenario's own fakes (the core calls setTimeout, clearTimeout,
    Date.now and console.warn by name, so a bare assignment in the sloppy-mode script replaces the global): a
    captured timer records its delay, so a case can pin that the one timer armed is the deadline's remainder and
    never a re-check."""

    FAKES = """
var TIMERS = [], WARNS = [], NOW = 5000000;
var realST = setTimeout, realCT = clearTimeout;
setTimeout = function (f, ms) { if (ms >= 100) { var t = { f: f, ms: ms, due: NOW + ms }; TIMERS.push(t); return t; } return realST(f, ms); };
clearTimeout = function (t) { var i = TIMERS.indexOf(t); if (i >= 0) TIMERS.splice(i, 1); else realCT(t); };
Date.now = function () { return NOW; };
console.warn = function () { WARNS.push(Array.prototype.join.call(arguments, " ")); };
function armed() { return TIMERS.map(function (t) { return t.ms; }); }
function runDue() { TIMERS.filter(function (t) { return t.due <= NOW; }).forEach(function (t) { TIMERS.splice(TIMERS.indexOf(t), 1); t.f(); }); }
"""

    def test_a_hold_that_ends_early_lands_the_reload_at_once_with_no_deadline_line(self):
        s = run_core(self.FAKES + """
var R = window.__rompReload; var shipping = 1;
window.__rompPaneBusy = function () { return shipping ? "upload" : ""; };   // render.ts: a ship awaits its ack
VERSION = { boot: "2.2", dist_ver: 7 }; R.checkBoot(); await tick(); await tick(); var held = state(); var heldArmed = armed();
emit("pointerup"); await tick(); var reasked = state(); var reaskedArmed = armed();   // a gesture's ending event re-asks and finds the hold still up
R.ended(); await tick(); var endedEarly = state();          // an ending event with the ship still pending: still held
NOW += 20000; shipping = 0; R.ended(); await tick();        // the last ack landed 20 s in: endReloadHoldIfIdle calls ended()
out({ held: held, heldArmed: heldArmed, reasked: reasked, reaskedArmed: reaskedArmed, endedEarly: endedEarly, after: state(), armed: armed(), warns: WARNS });""")
        self.assertEqual(s["held"]["reloads"], 0, "held: no reload now")
        self.assertEqual(s["held"]["waiting"], "upload")
        self.assertEqual(s["held"]["owed"]["reason"], "restart", "armed, not dropped")
        self.assertEqual(s["heldArmed"], [60000], "one timer, the deadline's: no 500 ms re-check")
        self.assertEqual(s["reasked"]["reloads"], 0, "a gesture's end re-asks; the ship still holds")
        self.assertEqual(s["reasked"]["waiting"], "upload")
        self.assertEqual(s["reaskedArmed"], [60000], "the same word keeps its one timer: a re-ask stacks no second")
        self.assertEqual(s["endedEarly"]["reloads"], 0, "an ending event while a ship is still pending finds the hold still up")
        self.assertEqual(s["after"]["reloads"], 1, "the ack's ending event reloads at once")
        self.assertEqual(s["after"]["waiting"], "")
        self.assertEqual(s["after"]["stored"]["reason"], "restart")
        self.assertEqual(s["after"]["persisted"], 1, "the pane persisted before the reload, as always")
        self.assertEqual(s["after"]["released"], "", "no release note: the hold ended on its own event")
        self.assertEqual(s["armed"], [], "the deadline timer is disarmed with the hold")
        self.assertEqual(s["warns"], [], "no deadline line")

    def test_a_hold_with_no_end_lands_the_reload_at_the_deadline_and_says_which_word_in_the_console_and_the_note(self):
        # the fold's ruling (romp-general, 2026-09-09): an upload that never acks or nacks must not pin the page on the
        # old build for good; the deadline is the only exit besides ended(), and it is loud: one console line naming the
        # word, and a note the pane's pre-reload hook reads (released()) into the toasts the fresh page replays
        # the shim's 'sends' is not among the words: it has no deadline (the next test)
        for kind, subject in (("upload", "An upload"), ("held-send", "A message held behind an upload"), ("later-word", "A 'later-word' hold")):
            with self.subTest(kind=kind):
                s = run_core(self.FAKES + """
var R = window.__rompReload; var NOTE = null;
window.__rompPaneBusy = function () { return %s; };                          // the hold never ends
window.__rompPersistForReload = function () { PERSISTED++; NOTE = R.released(); };   // render.ts persistNoticesForReload reads the note here
R.noteVersion({ boot: "2.2", dist_ver: 7 }); var held = state(); var heldArmed = armed();
NOW += 59000; runDue(); var under = state(); var underWarns = WARNS.length;
NOW += 1000; runDue();
out({ held: held, heldArmed: heldArmed, under: under, underWarns: underWarns, after: state(), note: NOTE, warns: WARNS, armed: armed() });""" % json.dumps(kind))
                self.assertEqual(s["held"]["reloads"], 0)
                self.assertEqual(s["held"]["waiting"], kind)
                self.assertEqual(s["heldArmed"], [60000], "the deadline timer, armed once for the whole wait")
                self.assertEqual(s["under"]["reloads"], 0, "59 s in, still held")
                self.assertEqual(s["under"]["waiting"], kind)
                self.assertEqual(s["underWarns"], 0)
                self.assertEqual(s["after"]["reloads"], 1, "60 s: reloads anyway")
                self.assertEqual(s["after"]["waiting"], "")
                self.assertEqual(s["after"]["stored"]["reason"], "restart")
                self.assertEqual(s["after"]["persisted"], 1)
                self.assertEqual(len(s["warns"]), 1, s["warns"])
                self.assertIn("'%s' hold did not end within 60 s" % kind, s["warns"][0], "the console line names the word")
                self.assertEqual(s["note"], subject + " had not finished after 60 s, so the page reloaded without waiting longer.",
                                 "the note the pane persists names what the page waited for")
                self.assertEqual(s["after"]["released"], s["note"], "…and released() still answers it after the fire")
                self.assertEqual(s["armed"], [], "nothing armed after the fire")

    def test_a_sends_hold_with_no_end_never_reloads_and_leaves_no_timer_no_line_and_no_note(self):
        # The fold's review (F1/UI-1, 2026-09-09): the shim's 'sends' is true only while this pane's socket is NOT open
        # (send() queues when the socket is not open; ws.onopen flushes the queue and calls ended()), so a reload fired
        # over it lands on a kernel that is not answering the page and takes the queued prompt with it, which is the
        # loss the hold exists to prevent. The word has no deadline: the flush is its only end.
        s = run_core(self.FAKES + """
var R = window.__rompReload; var queued = 1; var NOTES = [];
window.__rompPaneBusy = function () { return queued ? "sends" : ""; };               // the shim: everConnected && queue.length > queuedDiag
window.__rompPersistForReload = function () { PERSISTED++; NOTES.push(R.released()); };
R.noteVersion({ boot: "2.2", dist_ver: 7 }); var held = state(); var heldArmed = armed();
NOW += 60000; runDue(); var atDeadline = state();
NOW += 600000; R.tryFire(); emit("pointerup"); await tick(); var later = state();     // ten minutes on: the poll and a gesture's end re-ask
queued = 0; R.ended(); await tick();                                                  // the flush in ws.onopen is the ending event
out({ held: held, heldArmed: heldArmed, atDeadline: atDeadline, later: later, after: state(), notes: NOTES, warns: WARNS, armed: armed() });""")
        self.assertEqual(s["held"]["reloads"], 0)
        self.assertEqual(s["held"]["waiting"], "sends", "the word is reported like any pane word")
        self.assertEqual(s["heldArmed"], [], "no timer: the word has no deadline")
        self.assertEqual(s["atDeadline"]["reloads"], 0, "60 s in: still held")
        self.assertEqual(s["atDeadline"]["waiting"], "sends")
        self.assertEqual(s["later"]["reloads"], 0, "eleven minutes in: still held")
        self.assertEqual(s["later"]["waiting"], "sends")
        self.assertEqual(s["after"]["reloads"], 1, "the flush ends the hold, and the reload lands on the reopened socket")
        self.assertEqual(s["after"]["released"], "", "no release note")
        self.assertEqual(s["notes"], [""], "the pane persisted once, before the reload, and read no note")
        self.assertEqual(s["warns"], [], "no console line")
        self.assertEqual(s["armed"], [])

    def test_a_hold_released_and_re_raised_does_not_inherit_the_old_clock(self):
        # The fold-4 review's F1 (2026-09-08): the clock was set on the first sight of the hold and never cleared, so a
        # ship raised after an earlier episode had cleared was reloaded out at once as soon as the FIRST sight was
        # 60 s old, with the console line naming that stale age. The clock counts consecutive time the word has been
        # THE blocker: tryFire zeroes it whenever anything else answers (another hold, or nothing).
        episode = """
var R = window.__rompReload; var shipping = 1;
window.__rompPaneBusy = function () { return shipping ? "upload" : ""; };
R.noteVersion({ boot: "2.2", dist_ver: 7 }); var first = state(); var firstArmed = armed();       // the first episode: held
NOW += 5000; shipping = 0; COMPOSER.value = "a draft"; document.activeElement = COMPOSER;
R.ended(); await tick(); var typing = state(); var typingArmed = armed();                          // the ack lands; the composer holds now
NOW += 61000; shipping = 1; document.activeElement = null; emit("focusout"); await tick();        // a new ship, then the blur
var reheld = state(); var reheldArmed = armed(); var reheldWarns = WARNS.length;
"""
        s = run_core(self.FAKES + episode + """
shipping = 0; R.ended(); await tick();
out({ first: first, firstArmed: firstArmed, typing: typing, typingArmed: typingArmed, reheld: reheld, reheldArmed: reheldArmed,
      reheldWarns: reheldWarns, after: state(), warns: WARNS, armed: armed() });""")
        self.assertEqual(s["first"]["waiting"], "upload")
        self.assertEqual(s["firstArmed"], [60000])
        self.assertEqual(s["typing"]["reloads"], 0)
        self.assertEqual(s["typing"]["waiting"], "typing", "the hold cleared; the composer is what holds now")
        self.assertEqual(s["typingArmed"], [], "a gesture word has no deadline: the upload's timer went with its clock")
        self.assertEqual(s["reheld"]["reloads"], 0, "the new ship is 0 s old: it holds, whatever the first sighting's age")
        self.assertEqual(s["reheld"]["waiting"], "upload")
        self.assertEqual(s["reheldArmed"], [60000], "a full 60 s for the new episode")
        self.assertEqual(s["reheldWarns"], 0)
        self.assertEqual(s["after"]["reloads"], 1, "the second episode ends on its own ack")
        self.assertEqual(s["warns"], [], "no deadline line in either episode")
        self.assertEqual(s["armed"], [])
        # the second episode runs its own full 60 s, and the console line measures it, not the page's first sighting
        s2 = run_core(self.FAKES + episode + """
NOW += 59000; runDue(); var under = state(); var underWarns = WARNS.length;
NOW += 1000; runDue();
out({ under: under, underWarns: underWarns, after: state(), warns: WARNS, armed: armed() });""")
        self.assertEqual(s2["under"]["reloads"], 0, "59 s into the second episode: still held")
        self.assertEqual(s2["under"]["waiting"], "upload")
        self.assertEqual(s2["underWarns"], 0)
        self.assertEqual(s2["after"]["reloads"], 1, "60 s into the second episode: reloads anyway")
        self.assertEqual(len(s2["warns"]), 1, s2["warns"])
        self.assertIn("within 60 s", s2["warns"][0], "the line measures this episode, not the 125 s since the first sight")
        self.assertIn("after 60 s", s2["after"]["released"])
        self.assertEqual(s2["armed"], [])

    def test_a_change_of_word_starts_that_words_own_clock(self):
        # the shim's 'sends' (a prompt queued for the reopen) gives way to the pane's 'upload' (a re-ship awaiting its ack):
        # two holds; 'sends' has no clock (the fold's review, F1/UI-1), and the upload's timer is its own full 60 s from
        # the change of word, not measured from the first sight of the page's hold
        s = run_core(self.FAKES + """
var R = window.__rompReload; var word = "sends";
window.__rompPaneBusy = function () { return word; };
R.noteVersion({ boot: "2.2" }); var queued = state(); var queuedArmed = armed();
NOW += 30000; word = "upload"; R.ended(); await tick(); var shipping = state(); var shippingArmed = armed();   // the flush is the ending event; the re-ship holds now
NOW += 59000; runDue(); var under = state(); var underWarns = WARNS.length;                                   // 89 s after the first sight, 59 s into the upload's
NOW += 1000; runDue();
out({ queued: queued, queuedArmed: queuedArmed, shipping: shipping, shippingArmed: shippingArmed, under: under, underWarns: underWarns, after: state(), warns: WARNS });""")
        self.assertEqual(s["queued"]["waiting"], "sends")
        self.assertEqual(s["queuedArmed"], [], "a 'sends' hold arms no timer: it has no deadline")
        self.assertEqual(s["shipping"]["reloads"], 0)
        self.assertEqual(s["shipping"]["waiting"], "upload")
        self.assertEqual(s["shippingArmed"], [60000], "the upload's own timer, a full 60 s from the change of word")
        self.assertEqual(s["under"]["reloads"], 0, "59 s into the upload's clock: held")
        self.assertEqual(s["underWarns"], 0)
        self.assertEqual(s["after"]["reloads"], 1)
        self.assertEqual(len(s["warns"]), 1, s["warns"])
        self.assertIn("'upload' hold did not end within 60 s", s["warns"][0], "the word released is the one that ran out, at its own age")

    def test_a_gesture_word_has_no_deadline(self):
        # a reload mid-draft or mid-drag is what the core exists to prevent; the deadline is for the words whose ending
        # event belongs to a machine (an ack, a flush), not to the user
        s = run_core(self.FAKES + """
var R = window.__rompReload;
document.activeElement = COMPOSER; COMPOSER.value = "half a thought"; R.noteDv(8); var held = state(); var heldArmed = armed();
NOW += 600000; R.tryFire(); emit("input"); await tick(); var later = state();
emit("dragstart"); COMPOSER.value = ""; document.activeElement = null; emit("input"); await tick(); var dragging = state();
NOW += 600000; R.tryFire(); var stillDragging = state();
emit("dragend"); await tick();
out({ held: held, heldArmed: heldArmed, later: later, dragging: dragging, stillDragging: stillDragging, after: state(), warns: WARNS, armed: armed() });""")
        self.assertEqual(s["held"]["waiting"], "typing")
        self.assertEqual(s["heldArmed"], [], "no timer for a gesture word")
        self.assertEqual(s["later"]["reloads"], 0, "ten minutes into a draft: still held")
        self.assertEqual(s["later"]["waiting"], "typing")
        self.assertEqual(s["dragging"]["waiting"], "drag")
        self.assertEqual(s["stillDragging"]["reloads"], 0, "ten minutes into a drag: still held")
        self.assertEqual(s["after"]["reloads"], 1, "the gesture's own ending event fires")
        self.assertEqual(s["warns"], [])
        self.assertEqual(s["armed"], [])

    def test_a_panes_hold_holds_the_shells_reload_and_its_ending_event_releases_it(self):
        s = run_core(self.FAKES + """
var R = window.__rompReload; var paneHold = "upload";
IFRAMES = [{ contentWindow: { __rompReload: { busyHere: function () { return paneHold; } } } }];
R.request("restart", "2.2"); var held = state(); var heldArmed = armed();
paneHold = ""; R.tryFire();            // the pane's ended() reaches the shell's tryFire (the core forwards to shell())
out({ held: held, heldArmed: heldArmed, after: state(), armed: armed(), warns: WARNS });""")
        self.assertEqual(s["held"]["reloads"], 0)
        self.assertEqual(s["held"]["waiting"], "upload", "a pane's upload hold holds the shell's reload")
        self.assertEqual(s["heldArmed"], [60000], "the shell runs the deadline clock on the pane's word; no re-check")
        self.assertEqual(s["after"]["reloads"], 1)
        self.assertEqual(s["armed"], [])
        self.assertEqual(s["warns"], [])
        # the shell's deadline releases a pane's word too, and the pane's hook reads the note from the shell
        s2 = run_core(self.FAKES + """
var R = window.__rompReload; var NOTE = null;
var pane = { __rompReload: { busyHere: function () { return "upload"; }, released: function () { return window.__rompReload.released(); } },
             __rompPersistForReload: function () { PERSISTED += 10; NOTE = pane.__rompReload.released(); } };
IFRAMES = [{ contentWindow: pane }];
R.request("restart", "2.2");
NOW += 60000; runDue();
out({ after: state(), note: NOTE, warns: WARNS });""")
        self.assertEqual(s2["after"]["reloads"], 1)
        self.assertEqual(s2["after"]["persisted"], 11, "the shell and the pane persisted before the reload")
        self.assertIn("An upload had not finished after 60 s", s2["note"])
        self.assertEqual(len(s2["warns"]), 1)

    def test_a_pane_in_a_shell_reads_the_shells_release_note(self):
        s = run_core(self.FAKES + """
var shellNote = "";
window.parent = { __rompReload: { request: function () {}, tryFire: function () {}, released: function () { return shellNote; } } };
var R = window.__rompReload;
var own = R.released(); shellNote = "the shell's note"; var fromShell = R.released();
out({ inShell: R.inShell(), own: own, fromShell: fromShell });""")
        self.assertTrue(s["inShell"])
        self.assertEqual(s["own"], "", "nothing released")
        self.assertEqual(s["fromShell"], "the shell's note", "the shell decided the reload, so its note is the pane's to persist")
        s2 = run_core(self.FAKES + """
window.parent = { __rompReload: { request: function () {}, tryFire: function () {} } };   // an older shell core without the accessor
var R = window.__rompReload;
out({ own: R.released() });""")
        self.assertEqual(s2["own"], "", "a shell without released() reads as none, not a throw")

    def test_a_refused_reload_drops_the_release_note_and_its_clock(self):
        # The fold's review (F2, 2026-09-09): fire() persists before location.reload(), so the pane's hook had already
        # stored the release note among its pending toasts when the host refused; the catch clears the note and persists
        # once more, so the note the pane read LAST is empty and the next load replays no reload that never happened.
        s = run_core(self.FAKES + """
var R = window.__rompReload; REFUSE = true; var NOTES = [];
window.__rompPaneBusy = function () { return "upload"; };
window.__rompPersistForReload = function () { PERSISTED++; NOTES.push(R.released()); };   // render.ts persistNoticesForReload reads the note at each persist
R.noteDv(8);
NOW += 60000; runDue(); var refused = state(); var refusedArmed = armed(); var refusedNotes = NOTES.slice();
REFUSE = false; R.noteDv(9); var again = state(); var againArmed = armed();          // a strictly newer build re-arms: a fresh clock, no instant release
NOW += 59000; runDue(); var under = state();
NOW += 1000; runDue();
out({ refused: refused, refusedArmed: refusedArmed, refusedNotes: refusedNotes, again: again, againArmed: againArmed, under: under, after: state(), notes: NOTES, warns: WARNS });""")
        self.assertEqual(s["refused"]["reloads"], 1, "the deadline's reload was attempted")
        self.assertEqual(s["refused"]["waiting"], "refused")
        self.assertEqual(s["refused"]["released"], "", "a refused reload carries no release note forward")
        self.assertEqual(len(s["refusedNotes"]), 2, "the panes persisted before the attempt and once more after the refusal")
        self.assertIn("An upload had not finished after 60 s", s["refusedNotes"][0], "the note rode the persist before the attempt, as it must for a reload that lands")
        self.assertEqual(s["refusedNotes"][-1], "", "the last persist read no note: the stored toasts drop it")
        self.assertEqual(s["refusedArmed"], [])
        self.assertEqual(s["again"]["reloads"], 1, "the newer build finds the same word up and waits for it")
        self.assertEqual(s["again"]["waiting"], "upload")
        self.assertEqual(s["againArmed"], [60000], "…on a clock of its own")
        self.assertEqual(s["under"]["reloads"], 1)
        self.assertEqual(s["after"]["reloads"], 2, "the second deadline reloads (and this host takes it)")
        self.assertEqual(len(s["warns"]), 2)
        self.assertEqual(len(s["notes"]), 3, "the second deadline's reload persisted once, with its own note")
        self.assertIn("after 60 s", s["notes"][2])

    def test_a_gesture_in_a_later_pane_outranks_an_upload_hold_past_its_deadline(self):
        # The fold-4 review's K1 (2026-09-08): busy() returned the first pane's word without reading the panes behind
        # it, and past the deadline tryFire traded that word for a fire, so the shell reloaded while a later pane was
        # mid-gesture (the chat pane is the landing's first iframe, so this was the live ordering). busy() returns any
        # gesture from the shell or any pane first, and a pane word only when nothing else holds. Re-aimed at the fold's
        # review (UI-2, 2026-09-09): the gesture defers the release, it does not reset the upload's clock; the gesture's
        # end is the first gesture-free tryFire past the deadline, and the reload fires there at once.
        for gesture in ("drag", "pointer", "selection", "typing"):
            with self.subTest(gesture=gesture):
                s = run_core(self.FAKES + """
var R = window.__rompReload; var chatHold = "upload", paneGesture = "";
IFRAMES = [{ contentWindow: { __rompReload: { busyHere: function () { return chatHold; } } } },
           { contentWindow: { __rompReload: { busyHere: function () { return paneGesture; } } } }];
R.request("restart", "2.2"); var held = state(); var heldArmed = armed();
NOW += 61000; paneGesture = %s; runDue();                  // the deadline has passed, and a later pane is mid-gesture
var mid = state(); var midArmed = armed(); var midWarns = WARNS.length;
NOW += 30000; R.tryFire(); var still = state(); var stillArmed = armed();   // the poll re-asks mid-gesture: still deferred, no fresh clock
paneGesture = ""; R.tryFire();                            // the gesture's ending event calls the shell's tryFire
out({ held: held, heldArmed: heldArmed, mid: mid, midArmed: midArmed, midWarns: midWarns, still: still, stillArmed: stillArmed,
      after: state(), warns: WARNS, armed: armed() });""" % json.dumps(gesture))
                self.assertEqual(s["held"]["waiting"], "upload")
                self.assertEqual(s["heldArmed"], [60000])
                self.assertEqual(s["mid"]["reloads"], 0, "never mid-gesture, whatever the first pane says")
                self.assertEqual(s["mid"]["waiting"], gesture, "the gesture is the reason reported, not the pane's word")
                self.assertEqual(s["midArmed"], [], "the deadline timer fired into the gesture and is not re-armed: the gesture's own end is the next re-ask")
                self.assertEqual(s["midWarns"], 0, "no release while the gesture is up")
                self.assertEqual(s["still"]["reloads"], 0, "30 s further into the gesture: still deferred")
                self.assertEqual(s["still"]["waiting"], gesture)
                self.assertEqual(s["stillArmed"], [], "no fresh clock: the upload's clock ran on through the gesture")
                self.assertEqual(s["after"]["reloads"], 1, "the gesture's end is the first gesture-free tryFire past the deadline: the reload fires at once, with no fresh 60 s")
                self.assertEqual(s["after"]["waiting"], "")
                self.assertEqual(len(s["warns"]), 1, s["warns"])
                self.assertIn("'upload' hold did not end within 91 s", s["warns"][0], "the line measures the upload's whole wait, the gesture included")
                self.assertEqual(s["armed"], [])

    def test_intermittent_gestures_in_another_pane_do_not_restart_a_wedged_uploads_clock(self):
        # The fold's review (UI-2, 2026-09-09): with the clock zeroed by every gesture, a click or a selection in the
        # feed pane every 50 s restarted the wedged upload's 60 s each time, and the reload the backstop exists to land
        # never fired while the user was active. The clock is the pane word's: each gesture defers the fire, and the
        # first gesture-free tryFire past the deadline releases the word, however many gestures came before it.
        s = run_core(self.FAKES + """
var R = window.__rompReload; var chatHold = "upload", paneGesture = "";
IFRAMES = [{ contentWindow: { __rompReload: { busyHere: function () { return chatHold; } } } },
           { contentWindow: { __rompReload: { busyHere: function () { return paneGesture; } } } }];
R.request("restart", "2.2"); var held = state(); var heldArmed = armed();
var trace = [];
function mark() { trace.push({ t: (NOW - 5000000) / 1000, waiting: R.waiting, reloads: RELOADS, armed: armed().length }); }
for (var round = 0; round < 4; round++) {                             // a gesture every 50 s, each held for 15 s
  NOW += 50000; paneGesture = round % 2 ? "selection" : "pointer";    // t = 50, 115, ...: the gesture starts (no re-ask: only ends re-ask)
  NOW += 10000; runDue(); R.tryFire(); mark();                         // t = 60, 125, ...: the deadline timer, if armed, fires into the gesture; the poll re-asks
  NOW += 5000; paneGesture = ""; R.tryFire(); mark();                  // t = 65, 130, ...: the gesture's ending event
}
out({ held: held, heldArmed: heldArmed, trace: trace, after: state(), warns: WARNS, armed: armed() });""")
        self.assertEqual(s["held"]["waiting"], "upload")
        self.assertEqual(s["heldArmed"], [60000])
        self.assertEqual(s["trace"][0], {"t": 60, "waiting": "pointer", "reloads": 0, "armed": 0}, "60 s, mid-gesture: deferred, the timer spent and not re-armed")
        self.assertEqual(s["trace"][1], {"t": 65, "waiting": "", "reloads": 1, "armed": 0}, "65 s: the gesture's end is the first gesture-free tryFire past 60 s, and the reload fires")
        self.assertEqual([e["reloads"] for e in s["trace"]], [0, 1, 1, 1, 1, 1, 1, 1], "one reload; the later gestures find it already fired")
        self.assertEqual(s["after"]["reloads"], 1)
        self.assertEqual(len(s["warns"]), 1, s["warns"])
        self.assertIn("'upload' hold did not end within 65 s", s["warns"][0], "the line measures the upload's wait from its first sight")
        self.assertEqual(s["armed"], [])

    def test_a_gesture_in_the_uploads_own_page_does_not_restart_its_clock(self):
        # The fold's verification of UI-2 (2026-09-09, finding A): busyHere answers a window's own gesture before its
        # pane word, and busy() read only busyHere per window, so a click, a selection, a drag or a draft in the page
        # that OWNS the wedged upload hid the word: paneWord read '', clock() unclocked, and the word got a fresh 60 s
        # when the gesture ended (a reload at 125 s, its line saying 60 s). busy() now reads each window's gesture and
        # its pane word apart (paneHere), so the clock runs through a gesture in the word's own page too: the deadline
        # timer fires into the gesture and defers, and the gesture's end releases at once, the line naming the whole wait.
        gestures = {
            "pointer": ('emit("pointerdown");', 'emit("pointerup");'),
            "drag": ('emit("dragstart");', 'emit("dragend");'),
            "selection": ('SEL = { rangeCount: 1, isCollapsed: false, toString: function () { return "a passage"; } };',
                          'SEL = { rangeCount: 0, isCollapsed: true, toString: function () { return ""; } }; emit("selectionchange");'),
            "typing": ('COMPOSER.value = "a reply"; document.activeElement = COMPOSER;',
                       'document.activeElement = null; emit("focusout");'),
        }
        for gesture, (start, end) in gestures.items():
            with self.subTest(gesture=gesture):
                s = run_core(self.FAKES + """
var R = window.__rompReload; var NOTE = null;
window.__rompPaneBusy = function () { return "upload"; };                          // render.ts: a ship awaits an ack that never comes
window.__rompPersistForReload = function () { PERSISTED++; NOTE = R.released(); };
R.noteDv(8); var held = state(); var heldArmed = armed();
NOW += 30000; %s                                                                    // 30 s: the gesture starts in this page (a start is no re-ask)
NOW += 30000; runDue(); var mid = state(); var midArmed = armed(); var midWarns = WARNS.length;   // 60 s: the deadline timer fires into the gesture
NOW += 5000; %s await tick(); var after = state(); var afterArmed = armed();       // 65 s: the gesture's ending event
NOW += 60000; runDue(); R.tryFire(); var much = state();                            // 125 s: nothing left to fire
out({ held: held, heldArmed: heldArmed, mid: mid, midArmed: midArmed, midWarns: midWarns, after: after, afterArmed: afterArmed,
      much: much, note: NOTE, warns: WARNS, armed: armed() });""" % (start, end))
                self.assertEqual(s["held"]["waiting"], "upload")
                self.assertEqual(s["heldArmed"], [60000], "the upload's clock from its first sight")
                self.assertEqual(s["mid"]["reloads"], 0, "never mid-gesture")
                self.assertEqual(s["mid"]["waiting"], gesture, "the gesture is the word reported while it lives")
                self.assertEqual(s["midArmed"], [], "the deadline timer fired into the gesture and is not re-armed")
                self.assertEqual(s["midWarns"], 0)
                self.assertEqual(s["after"]["reloads"], 1, "the gesture's end is the first tryFire with nothing deferring past 60 s: the reload fires at once, with no fresh 60 s for the word hidden behind the gesture")
                self.assertEqual(s["after"]["waiting"], "")
                self.assertEqual(s["afterArmed"], [], "no fresh clock")
                self.assertEqual(len(s["warns"]), 1, s["warns"])
                self.assertIn("'upload' hold did not end within 65 s", s["warns"][0], "the line measures the upload's whole wait, the gesture in its own page included")
                self.assertEqual(s["note"], "An upload had not finished after 65 s, so the page reloaded without waiting longer.")
                self.assertEqual(s["much"]["reloads"], 1, "one reload")
                self.assertEqual(s["armed"], [])

    def test_a_gesture_in_the_pane_that_owns_the_upload_does_not_restart_its_clock_through_the_shell(self):
        # the same through a shell (finding A's shell configuration): the chat pane is the landing's first iframe, and
        # its busyHere answers its own gesture before its 'upload'; the shell reads the pane's word through paneHere
        s = run_core(self.FAKES + """
var R = window.__rompReload; var chatGesture = "";
var chat = { __rompReload: { busyHere: function () { return chatGesture || "upload"; }, paneHere: function () { return "upload"; } } };
IFRAMES = [{ contentWindow: chat }, { contentWindow: { __rompReload: { busyHere: function () { return ""; }, paneHere: function () { return ""; } } } }];
R.request("restart", "2.2"); var held = state(); var heldArmed = armed();
NOW += 30000; chatGesture = "pointer";                                              // 30 s: a click in the chat pane, where the upload lives
NOW += 30000; runDue(); var mid = state(); var midArmed = armed(); var midWarns = WARNS.length;   // 60 s: the timer fires into it
NOW += 5000; chatGesture = ""; R.tryFire(); var after = state(); var afterArmed = armed();        // 65 s: the pane's pointerup, its ended() reaching the shell's tryFire
NOW += 60000; runDue(); R.tryFire(); var much = state();
out({ held: held, heldArmed: heldArmed, mid: mid, midArmed: midArmed, midWarns: midWarns, after: after, afterArmed: afterArmed, much: much, warns: WARNS, armed: armed() });""")
        self.assertEqual(s["held"]["waiting"], "upload")
        self.assertEqual(s["heldArmed"], [60000])
        self.assertEqual(s["mid"]["reloads"], 0)
        self.assertEqual(s["mid"]["waiting"], "pointer", "the pane's gesture is the word reported")
        self.assertEqual(s["midArmed"], [], "fired into the gesture, not re-armed")
        self.assertEqual(s["midWarns"], 0)
        self.assertEqual(s["after"]["reloads"], 1, "the gesture's end releases at once: the shell read 'upload' behind the pane's gesture, so the clock ran on")
        self.assertEqual(s["afterArmed"], [])
        self.assertEqual(len(s["warns"]), 1, s["warns"])
        self.assertIn("'upload' hold did not end within 65 s", s["warns"][0])
        self.assertEqual(s["much"]["reloads"], 1)
        self.assertEqual(s["armed"], [])
        # an older pane core without paneHere is read through its busyHere word: it clocks when no gesture is up in it,
        # and a gesture there still hides its word (that pane keeps the pre-fix behaviour: a fresh 60 s at the gesture's end)
        s2 = run_core(self.FAKES + """
var R = window.__rompReload; var chatGesture = "";
IFRAMES = [{ contentWindow: { __rompReload: { busyHere: function () { return chatGesture || "upload"; } } } }];
R.request("restart", "2.2"); var held = state(); var heldArmed = armed();
NOW += 30000; chatGesture = "pointer";
NOW += 30000; runDue(); var mid = state(); var midArmed = armed();
NOW += 5000; chatGesture = ""; R.tryFire(); var after = state(); var afterArmed = armed();
NOW += 60000; runDue(); var much = state();
out({ held: held, heldArmed: heldArmed, mid: mid, midArmed: midArmed, after: after, afterArmed: afterArmed, much: much, warns: WARNS });""")
        self.assertEqual(s2["held"]["waiting"], "upload", "no gesture up: the busyHere word is the pane word")
        self.assertEqual(s2["heldArmed"], [60000], "and it clocks")
        self.assertEqual(s2["mid"]["waiting"], "pointer")
        self.assertEqual(s2["midArmed"], [])
        self.assertEqual(s2["after"]["reloads"], 0, "the older pane's word was hidden by its own gesture, so its clock restarted at the gesture's end (the fallback keeps that pane's pre-fix behaviour)")
        self.assertEqual(s2["after"]["waiting"], "upload")
        self.assertEqual(s2["afterArmed"], [60000])
        self.assertEqual(s2["much"]["reloads"], 1)
        self.assertIn("within 60 s", s2["warns"][0])

    def test_an_upload_beside_a_sibling_panes_sends_clocks_and_never_releases_over_it(self):
        # The fold's verification (2026-09-09, finding D): with the chat pane's 'upload' first and a sibling pane's
        # 'sends' behind it, paneWord was the first pane word found and the shell reloaded at 60 s over the sibling's
        # queued prompt; in the other order the upload never clocked while the 'sends' stood. busy() now records the
        # no-deadline word and the clocked word apart, whatever the order: 'sends' is the word reported (it defers a
        # release like a gesture), the upload's clock runs beside it, and the flush that ends the 'sends' releases the
        # upload at once, the line naming its whole wait.
        for order in ("chat-first", "sends-first"):
            with self.subTest(order=order):
                s = run_core(self.FAKES + """
var R = window.__rompReload; var chatHold = "upload", queued = 1; var NOTE = null;
var chat = { __rompReload: { busyHere: function () { return chatHold; }, paneHere: function () { return chatHold; } },
             __rompPersistForReload: function () { PERSISTED += 10; NOTE = window.__rompReload.released(); } };
var sib = { __rompReload: { busyHere: function () { return queued ? "sends" : ""; }, paneHere: function () { return queued ? "sends" : ""; } } };   // the shim: everConnected && queue.length > queuedDiag
IFRAMES = %s === "chat-first" ? [{ contentWindow: chat }, { contentWindow: sib }] : [{ contentWindow: sib }, { contentWindow: chat }];
R.request("restart", "2.2"); var held = state(); var heldArmed = armed();
NOW += 60000; runDue(); var atDeadline = state(); var atDeadlineArmed = armed(); var atDeadlineWarns = WARNS.length;   // 60 s: the upload's timer fires into the 'sends'
NOW += 30000; R.tryFire(); var later = state(); var laterArmed = armed();                                                // 90 s: the poll re-asks; still deferred
queued = 0; R.tryFire(); var after = state();                                                                            // the sibling's flush in ws.onopen: its ended() reaches the shell's tryFire
out({ held: held, heldArmed: heldArmed, atDeadline: atDeadline, atDeadlineArmed: atDeadlineArmed, atDeadlineWarns: atDeadlineWarns,
      later: later, laterArmed: laterArmed, after: after, note: NOTE, warns: WARNS, armed: armed() });""" % json.dumps(order))
                self.assertEqual(s["held"]["reloads"], 0)
                self.assertEqual(s["held"]["waiting"], "sends", "the no-deadline word is the one reported, ahead of the clocked word")
                self.assertEqual(s["heldArmed"], [60000], "the upload's clock runs beside the 'sends', whichever pane comes first")
                self.assertEqual(s["atDeadline"]["reloads"], 0, "60 s: no release over the 'sends': a reload would land on a kernel not answering the sibling and lose its prompt")
                self.assertEqual(s["atDeadline"]["waiting"], "sends")
                self.assertEqual(s["atDeadlineArmed"], [], "the timer fired into the 'sends' and is not re-armed: the flush is the next re-ask")
                self.assertEqual(s["atDeadlineWarns"], 0)
                self.assertEqual(s["later"]["reloads"], 0, "the poll 30 s on: still deferred")
                self.assertEqual(s["later"]["waiting"], "sends")
                self.assertEqual(s["laterArmed"], [], "no fresh clock")
                self.assertEqual(s["after"]["reloads"], 1, "the flush ends the 'sends', and the upload past its deadline is released at once")
                self.assertEqual(s["after"]["waiting"], "")
                self.assertEqual(s["after"]["persisted"], 11, "the shell and the chat pane persisted before the reload")
                self.assertEqual(len(s["warns"]), 1, s["warns"])
                self.assertIn("'upload' hold did not end within 90 s", s["warns"][0], "the line measures the upload's whole wait, the 'sends' included")
                self.assertEqual(s["note"], "An upload had not finished after 90 s, so the page reloaded without waiting longer.", "the chat pane's hook reads the shell's note")
                self.assertEqual(s["armed"], [])
        # the upload's ack lands first: its clock goes with the word, the 'sends' holds on with no clock, and the flush reloads with no note
        s = run_core(self.FAKES + """
var R = window.__rompReload; var chatHold = "upload", queued = 1;
IFRAMES = [{ contentWindow: { __rompReload: { busyHere: function () { return chatHold; }, paneHere: function () { return chatHold; } } } },
           { contentWindow: { __rompReload: { busyHere: function () { return queued ? "sends" : ""; }, paneHere: function () { return queued ? "sends" : ""; } } } }];
R.request("restart", "2.2");
NOW += 20000; chatHold = ""; R.tryFire(); var acked = state(); var ackedArmed = armed();   // the chat pane's ended()
NOW += 600000; R.tryFire(); var later = state();                                          // ten minutes on: the 'sends' still holds, no deadline
queued = 0; R.tryFire();
out({ acked: acked, ackedArmed: ackedArmed, later: later, after: state(), warns: WARNS, armed: armed() });""")
        self.assertEqual(s["acked"]["reloads"], 0)
        self.assertEqual(s["acked"]["waiting"], "sends")
        self.assertEqual(s["ackedArmed"], [], "the upload's clock went with its word; a 'sends' alone arms none")
        self.assertEqual(s["later"]["reloads"], 0, "a 'sends' hold has no deadline")
        self.assertEqual(s["after"]["reloads"], 1, "the flush reloads")
        self.assertEqual(s["after"]["released"], "", "no note: nothing was released")
        self.assertEqual(s["warns"], [])
        self.assertEqual(s["armed"], [])

    def test_a_gesture_in_a_later_pane_and_an_earlier_panes_upload_hold_each_end_on_their_own_event(self):
        # under the deadline both must end, in whichever order they land; the gesture is the word reported while it holds,
        # and the upload's clock runs underneath it
        for gesture in ("drag", "pointer", "selection", "typing"):
            with self.subTest(gesture=gesture):
                s = run_core(self.FAKES + """
var R = window.__rompReload; var chatHold = "upload", paneGesture = %s;
IFRAMES = [{ contentWindow: { __rompReload: { busyHere: function () { return chatHold; } } } },
           { contentWindow: { __rompReload: { busyHere: function () { return paneGesture; } } } }];
R.request("restart", "2.2"); var held = state(); var heldArmed = armed();
paneGesture = ""; R.tryFire(); var gestureOver = state(); var gestureOverArmed = armed();   // the gesture's ending event calls the shell's tryFire; the ship still holds
chatHold = ""; R.tryFire(); var shipOver = state();                                          // the ack lands: the chat pane's ended() reaches the shell
out({ held: held, heldArmed: heldArmed, gestureOver: gestureOver, gestureOverArmed: gestureOverArmed, shipOver: shipOver, armed: armed(), warns: WARNS });""" % json.dumps(gesture))
                self.assertEqual(s["held"]["reloads"], 0, "never mid-gesture, never mid-ship")
                self.assertEqual(s["held"]["waiting"], gesture, "the gesture outranks the first pane's word")
                self.assertEqual(s["heldArmed"], [60000], "the upload's clock runs from its first sight, gesture or not: the gesture only defers (the fold's review, UI-2)")
                self.assertEqual(s["gestureOver"]["reloads"], 0, "the gesture ended; the ship still holds")
                self.assertEqual(s["gestureOver"]["waiting"], "upload")
                self.assertEqual(s["gestureOverArmed"], [60000], "the same timer: the gesture's end changes the word reported, not the clock")
                self.assertEqual(s["shipOver"]["reloads"], 1, "both ended: the reload fires")
                self.assertEqual(s["armed"], [], "the clock went with the word")
                self.assertEqual(s["warns"], [])
        # the other order: the ack lands first, the later pane's gesture still holds, and its end fires
        s = run_core(self.FAKES + """
var R = window.__rompReload; var chatHold = "upload", paneGesture = "pointer";
IFRAMES = [{ contentWindow: { __rompReload: { busyHere: function () { return chatHold; } } } },
           { contentWindow: { __rompReload: { busyHere: function () { return paneGesture; } } } }];
R.request("restart", "2.2");
chatHold = ""; R.tryFire(); var shipOver = state();
paneGesture = ""; R.tryFire();
out({ shipOver: shipOver, after: state(), armed: armed() });""")
        self.assertEqual(s["shipOver"]["reloads"], 0, "the ack landed; the later pane is still mid-gesture")
        self.assertEqual(s["shipOver"]["waiting"], "pointer", "...and the gesture is the reason reported")
        self.assertEqual(s["after"]["reloads"], 1)
        self.assertEqual(s["armed"], [])

    def test_a_page_whose_pane_reports_no_hold_reloads_at_once_and_arms_no_timer(self):
        s = run_core(self.FAKES + """
var R = window.__rompReload;
window.__rompPaneBusy = function () { return ""; };       // nothing shipping, no send held behind the ship gate
R.noteVersion({ boot: "2.2", dist_ver: 7 });
out({ after: state(), armed: armed(), warns: WARNS });""")
        self.assertEqual(s["after"]["reloads"], 1)
        self.assertEqual(s["after"]["released"], "")
        self.assertEqual(s["armed"], [])
        self.assertEqual(s["warns"], [])


class ReloadWiringPinned(unittest.TestCase):
    def test_every_kernel_served_page_embeds_the_core_with_its_build_and_boot(self):
        shim = km._shim("feed", 123)
        self.assertIn("/*reload-core*/", shim)
        self.assertLess(shim.find("/*reload-core*/"), shim.find("/*shim-core*/"), "the core is defined before the shim asks it")
        self.assertIn("var LOADED=123,BOOT=%s," % json.dumps(km._BOOT_ID), shim)
        self.assertIn("/*reload-core*/", km._stale_block(123))
        self.assertIn("var LOADED=123,BOOT=%s," % json.dumps(km._BOOT_ID), km._stale_block(123))
        self.assertLess(km._stale_block(123).find("/*reload-core*/"), km._stale_block(123).find("var RL=window.__rompReload;"))
        self.assertIn("var LOADED=0,", km._reload_core())
        with self.assertRaises(RuntimeError):
            km._RELOAD_CORE_JS = km._RELOAD_CORE_JS.replace("/*end-reload-core*/", "", 1)
            try:
                km._reload_core_js()
            finally:
                km._RELOAD_CORE_JS = km._RELOAD_CORE_JS.replace("window.__rompReload=R;})();", "window.__rompReload=R;})();/*end-reload-core*/", 1)

    def test_the_shim_asks_the_core_on_build_drift_and_on_a_standalone_reconnect(self):
        js = km._shim("chat", 5)
        self.assertIn('function raiseBuild(){if(buildRaised)return;buildRaised=true;var R=window.__rompReload;\n'
                      'if(R){R.refused=function(){selfBar("A newer romp build is available.","build");};R.request("build","");}\n'
                      'else selfBar("A newer romp build is available.","build");}', js)
        self.assertNotIn('postMessage({romp:"wsStale",build:1}', js, "the build:1 hand-off to the banner is gone")
        self.assertIn('if(msg&&msg.type==="ka"){if(LOADEDV&&msg.dv&&msg.dv>LOADEDV)raiseBuild();', js, "the keepalive's dv is still the event")
        self.assertIn("if(window.__rompReload&&!window.__rompReload.inShell())window.__rompReload.checkBoot();", js)
        # the pane's queued sends hold the reload, and the flush is the ending event (review find, 2026-09-08)
        self.assertIn('window.__rompPaneBusy=function(){return (everConnected&&queue.length>queuedDiag)?"sends":"";};', js)
        self.assertIn("queue=[];queuedDiag=0;\ntry{if(window.__rompReload)window.__rompReload.ended();}catch(e){}", js)
        # a standalone page consumes its own marker; nobody else would
        self.assertIn("try{if(window.__rompReload&&!window.__rompReload.inShell())window.__rompReload.announce(null);}catch(e){}", js)
        # …on the RECONNECT branch only: the first open is not a restart
        i = js.find("if(wasReconn){")
        self.assertGreater(i, 0)
        self.assertLess(i, js.find("window.__rompReload.checkBoot();"))

    def test_the_shell_asks_on_its_own_sockets_reopen_and_feeds_its_keepalive(self):
        js = km._LANDING_MOBILE_JS
        self.assertIn("var shellOpened=false;", js)
        self.assertIn("if(shellOpened&&window.__rompReload)window.__rompReload.checkBoot();shellOpened=true;", js)
        self.assertIn("if(m&&m.type==='ka'){if(m.dv&&window.__rompReload)window.__rompReload.noteDv(m.dv);}", js)

    def test_the_banner_is_the_refused_fallback_and_the_poll_feeds_the_core(self):
        js = km._STALE_JS
        self.assertIn("if(RL){RL.refused=function(){buildStale=true;show(BUILDMSG);};", js)
        self.assertIn("RL.announce(function(k,t){if(window.__rompNotify)window.__rompNotify(k,t);});}", js)
        self.assertIn("if(RL)RL.noteVersion(v);", js)
        self.assertIn("if(loaded&&served>loaded&&served!==dismissed){if(!RL)show(BUILDMSG);}", js)
        self.assertIn("if(m.build){if(RL)RL.request('build','');else{buildStale=true;show(BUILDMSG);}}", js)
        self.assertIn("if(m&&m.romp==='wsFresh'){connStale=false;if(buildStale)show(BUILDMSG);else box.classList.remove('show');}", js,
                      "the CONNECTION prompt for a plain reconnect is untouched")

    def test_a_held_reload_is_told_to_the_notification_center_and_to_a_standalone_panes_bar(self):
        # the shell's stale script installs the `held` hook: the line names what the reload waits for (an upload, a held
        # send, queued sends) and skips momentary gesture holds; a standalone pane (no shell) raises its own bar
        js = km._STALE_JS
        self.assertIn("RL.held=function(b){var t=(b==='upload'?'The dashboard will reload once the upload in progress finishes.'", js)
        self.assertIn("if(t&&window.__rompNotify)window.__rompNotify('reload',t);", js)
        shim = km._shim("chat", 7) if callable(getattr(km, "_shim", None)) else ""
        self.assertIn("window.__rompReload.held=function(b){var t=(b==='upload'?", shim)
        self.assertIn("if(t)selfBar(t,'held');", shim)
        self.assertIn("!window.__rompReload.inShell()", shim, "only a standalone pane raises its own bar; in the shell the center speaks")

    def test_a_remote_kernels_restart_or_bundle_never_reaches_the_core(self):
        fed = open(os.path.join(ROOT, "ui", "webview", "federation.ts")).read()
        self.assertIn('if (msg && msg.type === "ka") return;', fed, "federation drops a remote kernel's keepalive")
        core = km._reload_core_js()
        self.assertNotIn("__rompLocalSend", core)
        self.assertNotIn("host", core, "the core knows no hosts: it reads THIS page's socket and /version only")
        self.assertIn("fetch('/version'", core, "…and /version is the serving kernel's own")

    def test_the_superseded_rule_is_recorded_with_both_dates(self):
        src = open(os.path.join(ROOT, "kernel", "kernel.py")).read()
        block = src[src.index("# ── the dashboard reloads ITSELF"):src.index("_RELOAD_CORE_JS = r")]
        self.assertIn("2026-09-08", block); self.assertIn("2026-07-13", block); self.assertIn("supersedes", block)
        ext = open(os.path.join(ROOT, "vscode-extension", "src", "extension.ts")).read()
        self.assertIn("2026-09-08", ext, "the VS Code exception names the ruling it stands beside")


if __name__ == "__main__":
    unittest.main()
