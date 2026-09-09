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
    clock is the word's: it starts when tryFire first sees the word block, runs while the same word keeps blocking,
    and zeroes whenever anything else answers (another word, a gesture, nothing), so a hold released and re-raised
    gets its own 60 s (the fold-4 review's F1); a gesture anywhere outranks a pane word (K1) and has no deadline.
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
        for kind, subject in (("upload", "An upload"), ("held-send", "A message held behind an upload"),
                              ("sends", "A message queued while the connection was down"), ("later-word", "A 'later-word' hold")):
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
        # two holds, two clocks; the second word's timer is a full 60 s, not the first word's remainder
        s = run_core(self.FAKES + """
var R = window.__rompReload; var word = "sends";
window.__rompPaneBusy = function () { return word; };
R.noteVersion({ boot: "2.2" }); var queued = state(); var queuedArmed = armed();
NOW += 30000; word = "upload"; R.ended(); await tick(); var shipping = state(); var shippingArmed = armed();   // the flush is the ending event; the re-ship holds now
NOW += 59000; runDue(); var under = state(); var underWarns = WARNS.length;                                   // 89 s after the first sight, 59 s into the upload's
NOW += 1000; runDue();
out({ queued: queued, queuedArmed: queuedArmed, shipping: shipping, shippingArmed: shippingArmed, under: under, underWarns: underWarns, after: state(), warns: WARNS });""")
        self.assertEqual(s["queued"]["waiting"], "sends")
        self.assertEqual(s["queuedArmed"], [60000])
        self.assertEqual(s["shipping"]["reloads"], 0)
        self.assertEqual(s["shipping"]["waiting"], "upload")
        self.assertEqual(s["shippingArmed"], [60000], "the new word's own timer replaces the old word's")
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
        s = run_core(self.FAKES + """
var R = window.__rompReload; REFUSE = true;
window.__rompPaneBusy = function () { return "upload"; };
R.noteDv(8);
NOW += 60000; runDue(); var refused = state(); var refusedArmed = armed();
REFUSE = false; R.noteDv(9); var again = state(); var againArmed = armed();          // a strictly newer build re-arms: a fresh clock, no instant release
NOW += 59000; runDue(); var under = state();
NOW += 1000; runDue();
out({ refused: refused, refusedArmed: refusedArmed, again: again, againArmed: againArmed, under: under, after: state(), warns: WARNS });""")
        self.assertEqual(s["refused"]["reloads"], 1, "the deadline's reload was attempted")
        self.assertEqual(s["refused"]["waiting"], "refused")
        self.assertEqual(s["refused"]["released"], "", "a refused reload carries no release note forward")
        self.assertEqual(s["refusedArmed"], [])
        self.assertEqual(s["again"]["reloads"], 1, "the newer build finds the same word up and waits for it")
        self.assertEqual(s["again"]["waiting"], "upload")
        self.assertEqual(s["againArmed"], [60000], "…on a clock of its own")
        self.assertEqual(s["under"]["reloads"], 1)
        self.assertEqual(s["after"]["reloads"], 2, "the second deadline reloads (and this host takes it)")
        self.assertEqual(len(s["warns"]), 2)

    def test_a_gesture_in_a_later_pane_outranks_an_upload_hold_past_its_deadline(self):
        # The fold-4 review's K1 (2026-09-08): busy() returned the first pane's word without reading the panes behind
        # it, and past the deadline tryFire traded that word for a fire, so the shell reloaded while a later pane was
        # mid-gesture (the chat pane is the landing's first iframe, so this was the live ordering). busy() returns any
        # gesture from the shell or any pane first, and a pane word only when nothing else holds; the gesture's end
        # hands the hold back to the word, whose clock runs from there.
        for gesture in ("drag", "pointer", "selection", "typing"):
            with self.subTest(gesture=gesture):
                s = run_core(self.FAKES + """
var R = window.__rompReload; var chatHold = "upload", paneGesture = "";
IFRAMES = [{ contentWindow: { __rompReload: { busyHere: function () { return chatHold; } } } },
           { contentWindow: { __rompReload: { busyHere: function () { return paneGesture; } } } }];
R.request("restart", "2.2"); var held = state();
NOW += 61000; paneGesture = %s; runDue();                  // the deadline has passed, and a later pane is mid-gesture
var mid = state(); var midArmed = armed(); var midWarns = WARNS.length;
paneGesture = ""; R.tryFire();                            // the gesture's ending event calls the shell's tryFire
var ended = state(); var endedArmed = armed();
NOW += 59000; runDue(); var under = state();
NOW += 1000; runDue();
out({ held: held, mid: mid, midArmed: midArmed, midWarns: midWarns, ended: ended, endedArmed: endedArmed, under: under,
      after: state(), warns: WARNS, armed: armed() });""" % json.dumps(gesture))
                self.assertEqual(s["held"]["waiting"], "upload")
                self.assertEqual(s["mid"]["reloads"], 0, "never mid-gesture, whatever the first pane says")
                self.assertEqual(s["mid"]["waiting"], gesture, "the gesture is the reason reported, not the pane's word")
                self.assertEqual(s["midArmed"], [], "a gesture has an ending event and no deadline: no timer")
                self.assertEqual(s["midWarns"], 0, "the deadline did not fire")
                self.assertEqual(s["ended"]["reloads"], 0, "the gesture's end hands the hold back to the pane's word")
                self.assertEqual(s["ended"]["waiting"], "upload")
                self.assertEqual(s["endedArmed"], [60000], "…which starts its own clock")
                self.assertEqual(s["under"]["reloads"], 0)
                self.assertEqual(s["after"]["reloads"], 1, "60 s after the gesture ended: reloads anyway")
                self.assertEqual(len(s["warns"]), 1, s["warns"])
                self.assertIn("within 60 s", s["warns"][0], "the clock ran from the gesture's end, not the first request")
                self.assertEqual(s["armed"], [])

    def test_a_gesture_in_a_later_pane_and_an_earlier_panes_upload_hold_each_end_on_their_own_event(self):
        # under the deadline both must end, in whichever order they land; the gesture is the word reported while it holds
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
                self.assertEqual(s["heldArmed"], [], "no clock while a gesture is the blocker")
                self.assertEqual(s["gestureOver"]["reloads"], 0, "the gesture ended; the ship still holds")
                self.assertEqual(s["gestureOver"]["waiting"], "upload")
                self.assertEqual(s["gestureOverArmed"], [60000], "the pane's word starts its clock when it becomes the blocker")
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
