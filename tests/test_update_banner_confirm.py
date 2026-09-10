#!/usr/bin/env python3
"""The update banner's Update button takes two clicks (2026-09-10).

One click used to POST /update, which converges main, rebuilds the served bundle and asks the manager
for a restart-all: every session on the box restarts and every turn in flight is cut. A click that only
meant to focus the dashboard window landed on that button. Now the first click ARMS the banner: the
Update button gives its place to a label that states the consequence, in counts (how many sessions the
restart stops and how many of them it interrupts, and whether other kernels restart too, or may), with
a red confirm button to the RIGHT of the label and a Cancel to its left, where Not now stood; only a
click on the confirm posts, carrying {"confirmed": true}. One gesture never posts, by layout: the second
activation of a double-click, a double-tap or a held key lands where the first did, on the label, which
covers Update's whole footprint and is not a control, whatever click count the engine reports, and the
confirm begins at least 24 px past Update's right edge, so a spread second tap misses it too. Belt and
braces on top: the confirm ignores a click whose detail is above 1 (the browser's own click count) and
the buttons ignore a repeated keydown (KeyboardEvent.repeat) for Enter and Space. The armed state is
dropped by exact events, never a timer: Cancel (a click, Enter or Space on it), Escape through the
shell's Escape chain, a press outside the banner in the shell document, a press or a focus in a pane
iframe, focus leaving the banner (a move between the label, the confirm and Cancel keeps it, and so does
a focusout to nothing under a PRIMARY press that began inside the box and has not ended: WebKit does not
focus a button on a press), the window losing focus, a hidden tab, and every re-render of the banner. The
click that focuses the window therefore never counts: the blur that took focus away disarmed the banner
first. The press ends with the click, a pointercancel, a pointerup outside the box or in a pane document,
a mouse pointer's pointerleave outside the box, or the window's blur; a secondary button or a second
finger never begins one. One ending is missing: a Firefox press released outside the window whose exit
delivers no leave beyond the box (seen under Playwright's synthetic mouse for a release past the right
edge, level with the banner) leaves the flag set until the next press, click or blur, and until then a
focusout to nothing disarms nothing; every gesture that leaves the banner still disarms it. An answer without counts drops the counts the banner held, so the label never
shows a previous kernel life's numbers; an answer without a registry count says the other kernels may
restart too, and a registry count without a session count says the other kernels restart too without
naming this kernel's sessions. The armed row is laid over the plain row it replaced, measured: the label
covers Update's footprint, Restart stands to its right on Update's row at every width from 640px up
whatever the label says (its text wraps inside it where the row is short of room), and Cancel never
shares a pixel with Not now; a resize while armed and the re-read's new text re-fit it.

EXECUTED, not pinned: node runs the kernel's _UPD_JS (the served banner script, as the browser receives
it) and the shell's Escape chain against fakes for document, window, location and fetch, one process per
scenario, and the scenario reads the banner's state back by name. Then real engines (Playwright's
Chromium, Firefox and WebKit, plus Firefox under Gecko's switch for the WebKit focus rule, skipped
loudly where absent) drive the served CSS, markup and script with real input: a double-click, a held
Enter, two taps at the Update button's point, a spread second tap past its right edge, a click and a tap
on the confirm, a real click on Cancel, a click and a drag on the banner's own text, Tab and Enter on
Cancel, Escape, a press inside a same-origin iframe, Tab out of the banner into the iframe, the
phone-width layout and the armed row's geometry against the plain row's at five widths. The kernel side
(the route's refusal of an unconfirmed body, the audit row, the counts and the registry read on
/update-check, with its timeout and its stderr line) is in tests/test_kernel_update.py. Synthetic values
only."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
km = load_source("romp_kernel_upd_confirm", os.path.join(BIN, "romp-kernel"))

# The page the banner script thinks it runs in. `var` at module scope shadows node's globals; the
# script's document and window listeners land in LISTENERS/WLISTENERS (each with the capture flag it
# was registered with), an element's own listeners in its `listeners`, so a scenario can emit the
# gesture events by name (with a relatedTarget, a key, a repeat flag), and every fetch is recorded with
# its method and body. An element's focus() records itself as document.activeElement; a pane document
# carries a window of its own (defaultView) with listeners of its own. There is no layout: elements have
# a style object and no getBoundingClientRect, so the label's fit step (the Browser leg measures it)
# does nothing here.
HARNESS = r"""
var LISTENERS = {}, WLISTENERS = {}, FETCHES = [], RELOADS = 0, FOCUS = [], PREVENTED = 0, STOPPED = 0;
function capFlag(cap) { return cap === true || !!(cap && cap.capture); }
function el(id) {
  var classes = {};
  var e = { id: id, hidden: false, disabled: false, textContent: "", onclick: null, children: [], listeners: {}, style: {},
    classList: { add: function (c) { classes[c] = 1; }, remove: function (c) { delete classes[c]; },
                 contains: function (c) { return !!classes[c]; } },
    addEventListener: function (t, f, cap) { (e.listeners[t] = e.listeners[t] || []).push({ f: f, cap: capFlag(cap) }); },
    focus: function () { document.activeElement = e; FOCUS.push(e.id); },
    contains: function (n) {
      if (n === e) return true;
      for (var i = 0; i < e.children.length; i++) if (e.children[i].contains(n)) return true;
      return false;
    } };
  return e;
}
var BOX = el("rupd"), MSG = el("rup-msg"), GO = el("rupd-go"), LBL = el("rupd-armed"), CF = el("rupd-confirm"),
    CX = el("rupd-cancel"), DM = el("rupd-dismiss");
var ELSEWHERE = el("elsewhere");                     // a node outside the banner
var IFRAME = el("pane-frame");                       // the shell document's element for a pane, outside the banner
BOX.children = [MSG, GO, LBL, CF, CX, DM];
GO.textContent = "Update"; CF.textContent = "Restart"; LBL.hidden = true; CF.hidden = true; CX.hidden = true;   // the served markup's initial state
BOX.querySelector = function (sel) { return sel === ".rup-msg" ? MSG : null; };
// the pane iframes: same-origin documents of their own, whose events never reach the shell document
function paneDoc(readyState) {
  var d = { readyState: readyState || "complete", listeners: {}, defaultView: { listeners: {} } };
  d.addEventListener = function (t, f, cap) { (d.listeners[t] = d.listeners[t] || []).push({ f: f, cap: capFlag(cap) }); };
  d.defaultView.addEventListener = function (t, f, cap) { (d.defaultView.listeners[t] = d.defaultView.listeners[t] || []).push({ f: f, cap: capFlag(cap) }); };
  return d;
}
function frame(id, readyState) {
  var f = { id: id, listeners: {}, contentDocument: paneDoc(readyState) };
  f.addEventListener = function (t, fn, cap) { (f.listeners[t] = f.listeners[t] || []).push({ f: fn, cap: capFlag(cap) }); };
  return f;
}
var PANE = frame("f-chat"), FRAMES = [PANE];
var document = {
  hidden: false, activeElement: null,
  addEventListener: function (t, f, cap) { (LISTENERS[t] = LISTENERS[t] || []).push({ f: f, cap: capFlag(cap) }); },
  getElementById: function (id) { return { "rupd": BOX, "rupd-go": GO, "rupd-armed": LBL, "rupd-confirm": CF,
                                           "rupd-cancel": CX, "rupd-dismiss": DM }[id] || null; },
  getElementsByTagName: function (t) { return t === "iframe" ? FRAMES : []; }
};
var window = { addEventListener: function (t, f, cap) { (WLISTENERS[t] = WLISTENERS[t] || []).push({ f: f, cap: capFlag(cap) }); } };
var location = { reload: function () { RELOADS++; } };
var CHECK = { cur: "v0.1.0", tag: "v0.2.0", mode: "ask", state: "", boot: "b1", drift: "", driftSha: "", sessions: 3, midTurn: 1, otherKernels: 0 };
var UPDATE_OK = true, UPDATE_TEXT = "";
function fetch(u, o) {
  var rec = { url: u, method: (o && o.method) || "GET", body: o && o.body ? JSON.parse(o.body) : null,
              type: (o && o.headers && o.headers["Content-Type"]) || "" };
  FETCHES.push(rec);
  if (u === "/update-check") return Promise.resolve({ ok: true, status: 200,
    json: function () { return Promise.resolve(JSON.parse(JSON.stringify(CHECK))); } });
  if (u === "/update") return Promise.resolve({ ok: UPDATE_OK, status: UPDATE_OK ? 200 : 400,
    json: function () { return Promise.resolve({ ok: UPDATE_OK }); }, text: function () { return Promise.resolve(UPDATE_TEXT); } });
  return Promise.reject(new Error("unexpected fetch " + u));
}
// a pointer event is a primary mouse press unless the scenario says otherwise (button, isPrimary, pointerType)
function emit(t, ev) {
  ev = ev || {};
  if (t.indexOf("pointer") === 0) { if (ev.button === undefined) ev.button = 0; if (ev.isPrimary === undefined) ev.isPrimary = true; if (ev.pointerType === undefined) ev.pointerType = "mouse"; }
  (LISTENERS[t] || []).forEach(function (l) { l.f(ev); });
}
function wemit(t, ev) { (WLISTENERS[t] || []).forEach(function (l) { l.f(ev || {}); }); }
function eemit(e, t, ev) { (e.listeners[t] || []).forEach(function (l) { l.f(ev || {}); }); }
function key(k, repeat) { return { key: k, repeat: !!repeat, preventDefault: function () { PREVENTED++; }, stopPropagation: function () { STOPPED++; } }; }
function tick() { return new Promise(function (r) { setTimeout(r, 0); }); }
function posts() { return FETCHES.filter(function (f) { return f.url === "/update"; }); }
function caps(ls) { return (ls || []).map(function (l) { return l.cap; }); }
function state() {
  return { shown: BOX.classList.contains("show"), msg: MSG.textContent, go: GO.textContent, label: LBL.textContent,
           armed: BOX.classList.contains("rup-arm"), goHidden: GO.hidden, goDisabled: GO.disabled,
           labelHidden: LBL.hidden, confirmHidden: CF.hidden, cancelHidden: CX.hidden, notNowHidden: DM.hidden, posts: posts(),
           checks: FETCHES.filter(function (f) { return f.url === "/update-check"; }).length, reloads: RELOADS,
           pointerdownCapture: caps(LISTENERS.pointerdown),
           boxFocusout: (BOX.listeners.focusout || []).length, goFocusout: (GO.listeners.focusout || []).length,
           paneWired: FRAMES.map(function (f) { return caps(f.contentDocument.listeners.pointerdown); }),
           paneUp: FRAMES.map(function (f) { return caps(f.contentDocument.listeners.pointerup); }),
           resizeListeners: (WLISTENERS.resize || []).length,
           paneFocus: FRAMES.map(function (f) { return caps(f.contentDocument.defaultView.listeners.focus); }),
           paneLoad: FRAMES.map(function (f) { return (f.listeners.load || []).length; }),
           focus: FOCUS.slice(), active: document.activeElement ? document.activeElement.id : "",
           prevented: PREVENTED, stopped: STOPPED };
}
// the wait after a confirmed POST polls /update-check on a 3 s timer; the scenario ends the process
// once its result is out, so no poll ever fires
function out(o) { process.stdout.write("RESULT:" + JSON.stringify(o) + "\n"); setTimeout(function () { process.exit(0); }, 0); }
"""


def run_banner(scenario, check=None):
    """Run the served banner script and the shell's Escape chain, let the load-time /update-check land
    (two ticks) so the offer shows, then the scenario. `check` overrides fields of the /update-check
    answer before the load."""
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed")
    pre = "".join("CHECK[%s] = %s;\n" % (json.dumps(k), json.dumps(v)) for k, v in (check or {}).items())
    d = tempfile.mkdtemp(prefix="upd-banner-")
    path = os.path.join(d, "banner.js")
    with open(path, "w") as f:
        f.write(HARNESS + pre + km._UPD_JS + "\n" + km._LANDING_ESC_JS + "\n(async function(){\nawait tick(); await tick();\n"
                + scenario + "\n})();\n")
    r = subprocess.run([node, path], capture_output=True, text=True, timeout=60)
    shutil.rmtree(d, ignore_errors=True)
    if r.returncode != 0:
        raise AssertionError("node failed:\n" + r.stderr)
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("RESULT:")), None)
    assert line, "no RESULT line:\n" + r.stdout
    return json.loads(line[len("RESULT:"):])


class TwoClicks(unittest.TestCase):
    def test_the_first_click_arms_with_the_counts_and_posts_nothing(self):
        s = run_banner("""
var before = state(); GO.onclick(); var atOnce = state(); await tick(); await tick();
out({ before: before, atOnce: atOnce, settled: state() });""")
        b = s["before"]
        self.assertEqual((b["shown"], b["go"], b["labelHidden"], b["confirmHidden"], b["cancelHidden"], b["notNowHidden"], b["armed"]),
                         (True, "Update", True, True, True, False, False), "the offer as served: Update and Not now")
        a = s["atOnce"]
        self.assertEqual(a["posts"], [], "the first click posts nothing")
        self.assertTrue(a["armed"])
        self.assertEqual(a["label"], "Restart 3 sessions now, interrupting 1",
                         "the label states the consequence, from the counts the banner holds")
        self.assertEqual((a["labelHidden"], a["confirmHidden"], a["cancelHidden"], a["notNowHidden"], a["goDisabled"]),
                         (False, False, False, True, False),
                         "the label, the confirm and Cancel stand in the armed row; Not now steps aside")
        self.assertEqual(a["go"], "Update", "the Update button keeps its text: it is hidden, not relabelled")
        self.assertEqual(a["active"], "rupd-armed", "focus rests on the label, not on the confirm")
        self.assertEqual(a["checks"], 2, "the arm re-reads /update-check for the counts as they stand now")
        self.assertTrue(a["shown"])
        self.assertEqual(s["settled"]["posts"], [], "still nothing posted once the re-read landed")
        self.assertTrue(s["settled"]["armed"])

    def test_the_arm_re_reads_the_counts_and_the_label_follows(self):
        s = run_banner("""
CHECK.sessions = 5; CHECK.midTurn = 2;                 // the box changed since the page loaded
GO.onclick(); var atOnce = state(); await tick(); await tick();
out({ atOnce: atOnce, after: state() });""")
        self.assertEqual(s["atOnce"]["label"], "Restart 3 sessions now, interrupting 1", "the held answer, at once")
        self.assertEqual(s["after"]["label"], "Restart 5 sessions now, interrupting 2", "the re-read's answer")
        self.assertEqual(s["after"]["posts"], [])

    def test_the_label_reads_naturally_for_one_session_nothing_to_stop_and_nothing_interrupted(self):
        # the empty case claims only what is counted: the sessions a restart stops (a tmux session
        # survives it, so a box of tmux sessions is rightly "nothing to interrupt", not "no sessions")
        cases = ((1, 1, "Restart 1 session now, interrupting 1"),
                 (4, 0, "Restart 4 sessions now"),
                 (0, 0, "Restart now, nothing to interrupt"))
        for sessions, mid, want in cases:
            s = run_banner("GO.onclick(); await tick(); await tick(); out(state());",
                           check={"sessions": sessions, "midTurn": mid})
            self.assertEqual(s["label"], want, (sessions, mid))
            self.assertEqual(s["posts"], [])

    def test_the_label_says_the_counts_are_this_kernels_when_another_kernel_restarts_too(self):
        # _restart_impact counts this kernel's sessions; the manager's restart-all restarts every kernel
        # in its registry. /update-check's otherKernels (the registry entries that are not this kernel)
        # decides the wording: with another kernel the label places the counts here and says the other
        # restarts too (one kernel: singular; several: plural); with one kernel the plain form; and when
        # the manager did not answer the read (null, or the field absent) the label says the other kernels
        # MAY restart too, never the single-kernel form, since a manager that missed a 1 s read can still
        # take the restart request
        null_tail = "; the other kernels may restart too (the manager did not answer)"
        cases = ((1, 3, 1, "Restart 3 sessions here now, interrupting 1; the other kernel restarts too"),
                 (2, 1, 1, "Restart 1 session here now, interrupting 1; the other kernels restart too"),
                 (5, 3, 0, "Restart 3 sessions here now; the other kernels restart too"),
                 (1, 4, 0, "Restart 4 sessions here now; the other kernel restarts too"),
                 (1, 0, 0, "Restart now, nothing to interrupt here; the other kernel restarts too"),
                 (0, 3, 1, "Restart 3 sessions now, interrupting 1"),
                 (None, 3, 1, "Restart 3 sessions here now, interrupting 1" + null_tail),
                 (None, 0, 0, "Restart now, nothing to interrupt here" + null_tail))
        for others, sessions, mid, want in cases:
            s = run_banner("GO.onclick(); await tick(); await tick(); out(state());",
                           check={"otherKernels": others, "sessions": sessions, "midTurn": mid})
            self.assertEqual(s["label"], want, (others, sessions, mid))
            self.assertEqual(s["posts"], [])
        s = run_banner("delete CHECK.otherKernels; GO.onclick(); await tick(); await tick(); out(state());")
        self.assertEqual(s["label"], "Restart 3 sessions here now, interrupting 1" + null_tail, "the field absent: unknown, never 0")
        # the two counts are known apart: no session count yet (the boot window) with a registry count
        # keeps the other-kernel clause and names no sessions; neither known says both
        for others, want in ((2, "Restart every session here now; the other kernels restart too"),
                             (1, "Restart every session here now; the other kernel restarts too"),
                             (0, "Restart every session now"),
                             (None, "Restart every session here now" + null_tail)):
            s = run_banner("GO.onclick(); await tick(); await tick(); out(state());",
                           check={"otherKernels": others, "sessions": None, "midTurn": None})
            self.assertEqual((s["label"], s["armed"], s["posts"]), (want, True, []), others)
        s = run_banner("delete CHECK.otherKernels; GO.onclick(); await tick(); await tick(); out(state());", check={"sessions": None, "midTurn": None})
        self.assertEqual(s["label"], "Restart every session here now" + null_tail, "neither count, the field absent")
        # the re-read's answer moves the wording too (a kernel added since the page loaded)
        s = run_banner("""
CHECK.otherKernels = 1; GO.onclick(); var atOnce = state(); await tick(); await tick(); out({ atOnce: atOnce, after: state() });""")
        self.assertEqual(s["atOnce"]["label"], "Restart 3 sessions now, interrupting 1")
        self.assertEqual(s["after"]["label"], "Restart 3 sessions here now, interrupting 1; the other kernel restarts too")

    def test_unknown_counts_arm_with_the_label_without_counts_and_the_re_read_fills_them_in(self):
        # /update-check answers null while the kernel's SDK backend is still being built: the banner
        # must still arm (never a plain-looking Update with armed set) and must not claim 0/0. Both offer
        # paths: the load-time offer and the kernel push
        for name, check, push in (
                ("load", {"sessions": None, "midTurn": None}, ""),
                ("push", {"mode": "", "tag": "", "sessions": None, "midTurn": None},
                 "window.__rompUpdateOffer('v0.1.0','v0.2.0','','b1','');")):
            s = run_banner(push + """
CHECK.sessions = 2; CHECK.midTurn = 0;               // the kernel knows by the time of the click
GO.onclick(); var atOnce = state(); await tick(); await tick(); var filled = state();
CF.onclick(); await tick(); out({ atOnce: atOnce, filled: filled, after: state() });""", check=check)
            a = s["atOnce"]
            self.assertEqual((a["label"], a["armed"], a["posts"], a["shown"]),
                             ("Restart every session now", True, [], True), name)
            self.assertEqual(s["filled"]["label"], "Restart 2 sessions now", name + ": the arm's re-read fills the counts in")
            self.assertEqual(len(s["after"]["posts"]), 1, name + ": the click on the confirm posts once")

    def test_an_answer_without_counts_drops_the_held_counts(self):
        # counts held from a previous kernel life must not survive an answer that has none: the label
        # falls back to its count-less form (the field null, and the field absent, as an older kernel
        # answers); a failed read is no information and keeps what is held
        for name, pre in (("null", "CHECK.sessions = null; CHECK.midTurn = null;"),
                          ("absent", "delete CHECK.sessions; delete CHECK.midTurn;")):
            s = run_banner(pre + """
GO.onclick(); var atOnce = state(); await tick(); await tick(); out({ atOnce: atOnce, after: state() });""")
            self.assertEqual(s["atOnce"]["label"], "Restart 3 sessions now, interrupting 1", name + ": the held counts, at once")
            a = s["after"]
            self.assertEqual((a["label"], a["armed"], a["posts"], a["checks"]),
                             ("Restart every session now", True, [], 2), name + ": the re-read had no counts; the label says so")
        s = run_banner("""
var realFetch = fetch; fetch = function (u, o) { if (u === "/update-check") return Promise.reject(new Error("down")); return realFetch(u, o); };
GO.onclick(); await tick(); await tick(); out(state());""")
        self.assertEqual((s["label"], s["armed"]), ("Restart 3 sessions now, interrupting 1", True), "a failed read keeps the held counts")

    def test_a_page_loaded_while_the_update_runs_holds_no_counts(self):
        # the kernel answers no counts while the update runs (its registry read is skipped: no label can be
        # worded then) and the banner records none from that answer either, so when the update fails and
        # the offer comes back the arm shows the count-less label until its own re-read lands, never a
        # count that arrived with the wait
        s = run_banner("""
var waited = state(); GO.onclick(); var atOnce = state(); await tick(); await tick();
out({ waited: waited, atOnce: atOnce, after: state() });""", check={"state": "running", "failed": "the install failed", "sessions": 3, "midTurn": 1, "otherKernels": 1})
        self.assertTrue(s["waited"]["msg"].startswith("The update did not finish: the install failed"), s["waited"]["msg"])
        self.assertEqual((s["waited"]["goHidden"], s["waited"]["armed"]), (False, False), "the offer is back")
        self.assertEqual((s["atOnce"]["label"], s["atOnce"]["armed"]), ("Restart every session now", True),
                         "the arm shows no counts: the answer that came with the wait recorded none")
        self.assertEqual(s["after"]["label"], "Restart 3 sessions here now, interrupting 1; the other kernel restarts too", "the arm's own re-read fills them in")

    def test_a_re_read_of_an_arm_that_ended_is_ignored_and_the_resize_listener_lives_with_the_armed_state(self):
        # the arm's re-read fits the label against the row it measured; an answer to a previous arm's
        # re-read landing during a later arm would set the label from an older answer (and fit it against
        # a row that is no longer on screen), so it is ignored. The window's resize listener is added at
        # the arm and removed at the disarm, so a resize while plain measures nothing
        s = run_banner("""
var pending = [], realFetch = fetch;
fetch = function (u, o) { if (u !== '/update-check') return realFetch(u, o);
  return new Promise(function (res) { pending.push(function (d) { res({ ok: true, status: 200, json: function () { return Promise.resolve(d); } }); }); }); };
var plain = state(); GO.onclick(); var armed1 = state(); CX.onclick(); var cancelled = state();
GO.onclick(); var armed2 = state();
pending[1]({ boot: 'b1', sessions: 5, midTurn: 2, otherKernels: 0 }); await tick(); await tick(); var second = state();
pending[0]({ boot: 'b1', sessions: 9, midTurn: 9, otherKernels: 0 }); await tick(); await tick(); var stale = state();
CX.onclick(); var done = state();
out({ plain: plain, armed1: armed1, cancelled: cancelled, armed2: armed2, second: second, stale: stale, done: done, reads: pending.length });""")
        self.assertEqual(s["reads"], 2, "each arm re-read once")
        self.assertEqual(s["second"]["label"], "Restart 5 sessions now, interrupting 2", "the current arm's answer")
        self.assertEqual((s["stale"]["label"], s["stale"]["armed"]), ("Restart 5 sessions now, interrupting 2", True), "the earlier arm's answer changes nothing")
        self.assertEqual([s[k]["resizeListeners"] for k in ("plain", "armed1", "cancelled", "armed2", "done")], [0, 1, 0, 1, 0],
                         "the resize listener is added at the arm and removed at the disarm")

    def test_the_boot_retire_drops_the_held_counts_as_well_as_the_armed_state(self):
        # a kernel restart under a showing offer retires it; the counts were that life's, so the next
        # arm shows the count-less label until its re-read lands
        s = run_banner("""
GO.onclick(); await tick(); await tick(); var armed1 = state();
window.__rompUpdBoot('b2'); var retired = state();
CHECK.boot = 'b2'; CHECK.sessions = 6; CHECK.midTurn = 2;
window.__rompUpdateOffer('v0.1.0', 'v0.3.0', '', 'b2', ''); GO.onclick(); var rearmed = state(); await tick(); await tick();
out({ armed1: armed1, retired: retired, rearmed: rearmed, after: state() });""")
        self.assertTrue(s["armed1"]["armed"])
        r = s["retired"]
        self.assertEqual((r["armed"], r["shown"], r["go"], r["labelHidden"], r["posts"]), (False, False, "Update", True, []))
        self.assertEqual((s["rearmed"]["armed"], s["rearmed"]["label"]), (True, "Restart every session now"),
                         "the old life's counts are gone at the instant of the arm")
        self.assertEqual(s["after"]["label"], "Restart 6 sessions now, interrupting 2", "the new life's counts, once read")

    def test_the_click_on_the_confirm_posts_once_with_the_confirmation(self):
        s = run_banner("""
GO.onclick(); await tick(); await tick();
CF.onclick(); var atOnce = state(); await tick(); await tick();
out({ atOnce: atOnce, after: state() });""")
        a = s["atOnce"]
        self.assertEqual(len(a["posts"]), 1, "the confirm posts")
        p = a["posts"][0]
        self.assertEqual((p["method"], p["body"], p["type"]), ("POST", {"confirmed": True}, "application/json"))
        self.assertTrue(a["goDisabled"], "acknowledged at once: the Update button comes back disabled under the wait")
        self.assertFalse(a["armed"], "the armed state ends with the click that used it")
        self.assertEqual((a["labelHidden"], a["confirmHidden"], a["cancelHidden"]), (True, True, True))
        self.assertTrue(a["msg"].startswith("Updating romp"))
        self.assertEqual(len(s["after"]["posts"]), 1, "once")
        self.assertEqual(s["after"]["reloads"], 0)

    def test_a_second_activation_of_the_update_button_never_posts(self):
        # the confirm is a different control, beside the label that took Update's place: whatever
        # reaches the Update button again (a double-click's second click, a double-tap's second tap, a
        # held key's repeat, a synthetic click with any detail) arms at most, and only the confirm posts
        s = run_banner("""
GO.onclick({ detail: 1 }); GO.onclick({ detail: 2 }); var dbl = state(); await tick(); await tick();
GO.onclick({ detail: 1 }); GO.onclick({ detail: 0 }); GO.onclick(); var more = state(); await tick();
CF.onclick({ detail: 1 }); var confirmed = state(); await tick();
out({ dbl: dbl, more: more, confirmed: confirmed });""")
        self.assertEqual((s["dbl"]["posts"], s["dbl"]["armed"]), ([], True), "the double-click arms and stops")
        self.assertEqual((s["more"]["posts"], s["more"]["armed"]), ([], True), "later activations of Update change nothing")
        self.assertEqual(len(s["confirmed"]["posts"]), 1, "a click on the confirm posts")

    def test_the_confirm_ignores_a_multi_click_and_takes_a_keyboard_activation(self):
        # belt and braces under the layout: a click event on the confirm with the browser's click count
        # above 1 is swallowed and the banner stays armed; Enter or Space on the focused confirm is a
        # click with detail 0 and confirms
        s = run_banner("""
GO.onclick(); await tick(); CF.onclick({ detail: 2 }); CF.onclick({ detail: 3 }); var multi = state(); await tick();
CF.onclick({ detail: 0 }); out({ multi: multi, keyboard: state() });""")
        self.assertEqual((s["multi"]["posts"], s["multi"]["armed"]), ([], True))
        self.assertEqual(len(s["keyboard"]["posts"]), 1)

    def test_a_repeated_enter_or_space_keydown_is_ignored_on_the_buttons_and_a_held_tab_is_not(self):
        # KeyboardEvent.repeat is the event's own flag for a held key's repeats: the Update button and
        # the confirm cancel the repeat's default (its activation) for Enter and Space only, so a held
        # Enter cannot arm and confirm in one gesture, and a held Tab still leaves the button
        s = run_banner("""
eemit(GO, 'keydown', key('Enter', false)); var first = PREVENTED;
eemit(GO, 'keydown', key('Enter', true)); eemit(GO, 'keydown', key(' ', true)); var goRepeats = PREVENTED;
eemit(CF, 'keydown', key('Enter', true)); eemit(CF, 'keydown', key(' ', true)); var cfRepeats = PREVENTED;
eemit(GO, 'keydown', key('Tab', true)); eemit(CF, 'keydown', key('Tab', true)); eemit(GO, 'keydown', key('a', true)); var others = PREVENTED;
out({ first: first, goRepeats: goRepeats, cfRepeats: cfRepeats, others: others,
      cancelHasNone: !(CX.listeners.keydown || []).length, state: state() });""")
        self.assertEqual(s["first"], 0, "the first keydown activates as ever")
        self.assertEqual(s["goRepeats"], 2, "a repeated Enter and a repeated Space on Update are cancelled")
        self.assertEqual(s["cfRepeats"], 4, "and on the confirm")
        self.assertEqual(s["others"], 4, "a held Tab or letter is left alone")
        self.assertEqual(s["state"]["posts"], [])

    def test_a_re_render_resets_the_confirm_state(self):
        # a new offer pushed by the kernel (a newer tag), the running flip (an update started in
        # another window), and the boot retire: each is a re-render, and each drops the armed state,
        # so the next click on the button arms again instead of posting
        s = run_banner("""
GO.onclick(); await tick(); var armed1 = state();
window.__rompUpdateOffer('v0.1.0', 'v0.3.0', '', 'b1', ''); var reoffered = state();
GO.onclick(); var rearmed = state(); await tick();
window.__rompUpdateOffer('', '', '', 'b1', 'running'); var running = state();
out({ armed1: armed1, reoffered: reoffered, rearmed: rearmed, running: running });""")
        self.assertTrue(s["armed1"]["armed"])
        r = s["reoffered"]
        self.assertEqual((r["armed"], r["go"], r["labelHidden"], r["confirmHidden"], r["cancelHidden"], r["notNowHidden"]),
                         (False, "Update", True, True, True, False))
        self.assertIn("v0.3.0", r["msg"])
        self.assertEqual((s["rearmed"]["armed"], s["rearmed"]["posts"]), (True, []), "arms again, posts nothing")
        self.assertEqual((s["running"]["armed"], s["running"]["goHidden"], s["running"]["posts"]), (False, True, []),
                         "the running flip hides Update (its own flag, which the armed state never touches)")

    def test_cancel_a_press_elsewhere_a_blur_or_a_hidden_tab_disarms_and_a_press_inside_does_not(self):
        s = run_banner("""
GO.onclick(); await tick(); CX.onclick(); var cancelled = state();
GO.onclick(); await tick(); emit('pointerdown', { target: LBL }); emit('pointerdown', { target: CF }); var inside = state();
emit('pointerdown', { target: ELSEWHERE }); var outside = state();
GO.onclick(); await tick(); wemit('blur'); var blurred = state();
GO.onclick(); await tick(); document.hidden = true; emit('visibilitychange'); var hidden = state();
document.hidden = false;
out({ cancelled: cancelled, inside: inside, outside: outside, blurred: blurred, hidden: hidden });""")
        c = s["cancelled"]
        self.assertEqual((c["armed"], c["go"], c["labelHidden"], c["confirmHidden"], c["cancelHidden"], c["notNowHidden"], c["shown"]),
                         (False, "Update", True, True, True, False, True), "Cancel: back to the offer, still showing")
        self.assertEqual(c["active"], "rupd-go", "Cancel with focus in the banner hands focus back to Update")
        self.assertTrue(s["inside"]["armed"], "a press on the label or the confirm keeps the armed state")
        self.assertFalse(s["outside"]["armed"], "a press anywhere else drops it")
        self.assertEqual(s["outside"]["pointerdownCapture"], [True],
                         "the document listener is capture-phase: a shell control that stops propagation cannot hide the press")
        self.assertEqual(s["outside"]["active"], "rupd-armed", "and leaves focus where the press will put it, never back on Update")
        self.assertFalse(s["blurred"]["armed"], "focus leaving the window drops it")
        self.assertFalse(s["hidden"]["armed"], "a hidden tab drops it")
        for k in ("cancelled", "inside", "outside", "blurred", "hidden"):
            self.assertEqual(s[k]["posts"], [], k)

    def test_focus_leaving_the_banner_disarms_and_a_move_within_it_does_not(self):
        # one focusout listener on the box (focusout bubbles from the label, the confirm and Cancel;
        # none on the Update button, which is hidden while armed): a relatedTarget inside the banner is a
        # move between its own controls, so Cancel and the confirm are clickable and Tab-reachable; any
        # other (another control, a frame, nothing) means attention left, and disarms
        s = run_banner("""
var plain = state(); eemit(BOX, 'focusout', { relatedTarget: ELSEWHERE }); var plainAfter = state();
GO.onclick(); await tick();
eemit(BOX, 'focusout', { relatedTarget: CF }); var toConfirm = state();
eemit(BOX, 'focusout', { relatedTarget: CX }); var toCancel = state();
eemit(BOX, 'focusout', { relatedTarget: LBL }); var toLabel = state();
eemit(BOX, 'focusout', { relatedTarget: ELSEWHERE }); var left = state();
GO.onclick(); await tick(); eemit(BOX, 'focusout', { relatedTarget: null }); var toNothing = state();
GO.onclick(); await tick(); eemit(BOX, 'focusout', { relatedTarget: IFRAME }); var toFrame = state();
GO.onclick(); var rearmed = state(); await tick();
out({ plain: plain, plainAfter: plainAfter, toConfirm: toConfirm, toCancel: toCancel, toLabel: toLabel,
      left: left, toNothing: toNothing, toFrame: toFrame, rearmed: rearmed });""")
        self.assertEqual((s["plain"]["boxFocusout"], s["plain"]["goFocusout"]), (1, 0), "one focusout listener, on the box")
        self.assertEqual((s["plainAfter"]["armed"], s["plainAfter"]["go"]), (False, "Update"), "a no-op while plain")
        for k in ("toConfirm", "toCancel", "toLabel"):
            self.assertTrue(s[k]["armed"], k + ": focus moved within the banner")
        for k in ("left", "toNothing", "toFrame"):
            self.assertEqual((s[k]["armed"], s[k]["labelHidden"], s[k]["cancelHidden"], s[k]["posts"]),
                             (False, True, True, []), k + ": focus left the banner: plain again")
        self.assertEqual(s["left"]["active"], "rupd-armed", "a focus leaving does not pull focus back")
        self.assertEqual((s["rearmed"]["armed"], s["rearmed"]["posts"]), (True, []), "the next click arms, never posts")

    def test_a_press_that_blurs_the_label_to_nothing_still_confirms_and_still_cancels(self):
        # WebKit (Safari, every iOS browser) does not focus a button on a press: the mousedown on the
        # confirm or Cancel blurs the label to nothing, so the box's focusout fires with relatedTarget null
        # BEFORE the click. The press began inside the box (the document's capture pointerdown records
        # it), so that focusout disarms nothing and the click that ends the gesture decides: the confirm
        # posts, Cancel's handler runs. A touch tap plays pointerup before the compatibility mousedown
        # that moves focus, so the flag must outlive pointerup: the tap sequence emits it first
        s = run_banner("""
GO.onclick(); await tick(); await tick();
emit('pointerdown', { target: CF }); eemit(BOX, 'focusout', { relatedTarget: null }); var midPress = state();
emit('click', { target: CF }); CF.onclick({ detail: 1 }); var confirmed = state(); await tick();
out({ midPress: midPress, confirmed: confirmed });""")
        self.assertEqual((s["midPress"]["armed"], s["midPress"]["confirmHidden"], s["midPress"]["posts"]), (True, False, []),
                         "the focusout under the press disarmed nothing")
        self.assertEqual(len(s["confirmed"]["posts"]), 1, "the click that ended the press posted")
        s = run_banner("""
GO.onclick(); await tick(); await tick();
emit('pointerdown', { target: CF }); emit('pointerup', { target: CF });
eemit(BOX, 'focusout', { relatedTarget: null }); var midTap = state();
emit('click', { target: CF }); CF.onclick({ detail: 1 }); var tapped = state(); await tick();
out({ midTap: midTap, tapped: tapped });""")
        self.assertTrue(s["midTap"]["armed"], "the press outlives pointerup: a tap's focus move comes after it")
        self.assertEqual(len(s["tapped"]["posts"]), 1, "the tap posted")
        s = run_banner("""
GO.onclick(); await tick(); await tick();
emit('pointerdown', { target: CX }); eemit(BOX, 'focusout', { relatedTarget: null }); document.activeElement = null; var midPress = state();
emit('click', { target: CX }); CX.onclick(); var cancelled = state();
out({ midPress: midPress, cancelled: cancelled });""")
        self.assertTrue(s["midPress"]["armed"])
        c = s["cancelled"]
        self.assertEqual((c["armed"], c["shown"], c["active"], c["posts"]), (False, True, "rupd-go", []),
                         "Cancel's own handler disarmed and handed focus back to Update, with nothing inside the banner focused")

    def test_a_press_on_the_banners_own_text_keeps_the_armed_state(self):
        # a press on the message text or the padding blurs the label to nothing in every engine (the text
        # is not focusable); it began inside the box, so nothing disarms, and the click that ends it clears
        # the press: the next focusout to nothing is focus leaving, and disarms
        s = run_banner("""
GO.onclick(); await tick(); await tick();
emit('pointerdown', { target: MSG }); eemit(BOX, 'focusout', { relatedTarget: null }); emit('click', { target: MSG }); var afterText = state();
eemit(BOX, 'focusout', { relatedTarget: null }); var afterLeave = state();
out({ afterText: afterText, afterLeave: afterLeave });""")
        self.assertEqual((s["afterText"]["armed"], s["afterText"]["posts"]), (True, []), "a click on the banner's own text disarms nothing")
        self.assertFalse(s["afterLeave"]["armed"], "the press ended with the click: a focusout to nothing disarms again")

    def test_a_focusout_to_nothing_without_a_press_inside_disarms(self):
        # the control for the rule above: a window blur, a script's blur or an engine's window switch reach
        # the box as a focusout with no relatedTarget and no press inside, and disarm. The flag does not
        # outlive the gesture that set it: a press inside that ended in a click (here a swallowed
        # multi-click), a pointercancel (a touch that became a scroll) or the window's blur is over, and
        # the next focusout to nothing disarms (the other endings, and the one shape that has none, are
        # the next two tests)
        s = run_banner("""
GO.onclick(); await tick(); await tick(); eemit(BOX, 'focusout', { relatedTarget: null }); var noPress = state();
GO.onclick(); emit('pointerdown', { target: CF }); emit('click', { target: CF }); CF.onclick({ detail: 2 }); var swallowed = state();
eemit(BOX, 'focusout', { relatedTarget: null }); var afterClick = state();
GO.onclick(); emit('pointerdown', { target: CF }); emit('pointercancel', {}); eemit(BOX, 'focusout', { relatedTarget: null }); var afterCancel = state();
GO.onclick(); emit('pointerdown', { target: CF }); wemit('blur'); var blurred = state();
GO.onclick(); eemit(BOX, 'focusout', { relatedTarget: null }); var afterBlur = state();
out({ noPress: noPress, swallowed: swallowed, afterClick: afterClick, afterCancel: afterCancel, blurred: blurred, afterBlur: afterBlur });""")
        self.assertEqual((s["swallowed"]["armed"], s["swallowed"]["posts"]), (True, []), "a multi-click on the confirm is swallowed, still armed")
        for k in ("noPress", "afterClick", "afterCancel", "blurred", "afterBlur"):
            self.assertEqual((s[k]["armed"], s[k]["posts"]), (False, []), k)

    def test_a_secondary_button_or_a_second_finger_never_begins_a_press(self):
        # a right or middle click inside the banner ends in auxclick and no click, so a flag it set would
        # outlive it: only a primary press (button 0, the primary pointer) sets the flag, and the focusout
        # to nothing after such a click disarms as it would without it. A right press on the message text
        # blurs the label to nothing at the mousedown, and with no press recorded that disarms at once
        # (before, the flag kept the banner armed until the next click or blur)
        s = run_banner("""
GO.onclick(); await tick(); await tick();
emit('pointerdown', { target: LBL, button: 2 }); emit('contextmenu', { target: LBL }); emit('pointerup', { target: LBL, button: 2 }); emit('auxclick', { target: LBL }); var afterRight = state();
eemit(BOX, 'focusout', { relatedTarget: null }); var rightBlur = state();
GO.onclick(); emit('pointerdown', { target: CF, button: 1 }); emit('pointerup', { target: CF, button: 1 }); emit('auxclick', { target: CF }); eemit(BOX, 'focusout', { relatedTarget: null }); var middleBlur = state();
GO.onclick(); emit('pointerdown', { target: CF, isPrimary: false }); eemit(BOX, 'focusout', { relatedTarget: null }); var secondFinger = state();
GO.onclick(); emit('pointerdown', { target: MSG, button: 2 }); eemit(BOX, 'focusout', { relatedTarget: null }); var rightText = state();
GO.onclick(); emit('pointerdown', { target: CF, button: 0 }); eemit(BOX, 'focusout', { relatedTarget: null }); var primary = state();
out({ afterRight: afterRight, rightBlur: rightBlur, middleBlur: middleBlur, secondFinger: secondFinger, rightText: rightText, primary: primary });""")
        self.assertTrue(s["afterRight"]["armed"], "the right click itself disarms nothing")
        for k in ("rightBlur", "middleBlur", "secondFinger", "rightText"):
            self.assertEqual((s[k]["armed"], s[k]["posts"]), (False, []), k + ": no press was recorded, so the focusout to nothing disarmed")
        self.assertTrue(s["primary"]["armed"], "the control: a primary press keeps the armed state under the same focusout")

    def test_a_press_released_outside_the_banner_or_in_a_pane_ends_and_a_taps_leave_chain_does_not(self):
        # a primary press that began inside the box and was released elsewhere ends without a click inside
        # the box: a pointerup outside the box in this document, a pointerup in a pane document (the shell
        # never sees it), or a mouse pointer's pointerleave on an element outside the box (the mouse left the
        # document while pressed). A touch tap's pointerup inside the box and its pointerleave chain (the
        # touch pointer leaves every element up to the root before the compatibility mousedown) end
        # nothing: the tap on the confirm still posts where the engine does not focus buttons
        s = run_banner("""
GO.onclick(); await tick(); await tick();
emit('pointerdown', { target: LBL }); emit('pointerup', { target: ELSEWHERE }); eemit(BOX, 'focusout', { relatedTarget: null }); var releasedOutside = state();
GO.onclick(); emit('pointerdown', { target: LBL }); eemit(PANE.contentDocument, 'pointerup'); eemit(BOX, 'focusout', { relatedTarget: null }); var releasedInPane = state();
GO.onclick(); emit('pointerdown', { target: LBL }); emit('pointerleave', { target: ELSEWHERE, pointerType: 'mouse' }); eemit(BOX, 'focusout', { relatedTarget: null }); var mouseLeft = state();
GO.onclick(); emit('pointerdown', { target: CF, pointerType: 'touch' }); emit('pointerup', { target: CF, pointerType: 'touch' });
emit('pointerleave', { target: CF, pointerType: 'touch' }); emit('pointerleave', { target: BOX, pointerType: 'touch' }); emit('pointerleave', { target: ELSEWHERE, pointerType: 'touch' });
eemit(BOX, 'focusout', { relatedTarget: null }); var tapChain = state();
emit('click', { target: CF }); CF.onclick({ detail: 1 }); var tapped = state();
out({ releasedOutside: releasedOutside, releasedInPane: releasedInPane, mouseLeft: mouseLeft, tapChain: tapChain, tapped: tapped, paneUp: tapped.paneUp });""")
        for k in ("releasedOutside", "releasedInPane", "mouseLeft"):
            self.assertEqual((s[k]["armed"], s[k]["posts"]), (False, []), k + ": the press ended, so the focusout to nothing disarmed")
        self.assertTrue(s["tapChain"]["armed"], "a tap's pointerup inside the box and its leave chain end nothing")
        self.assertEqual(len(s["tapped"]["posts"]), 1, "the tap posted")
        self.assertEqual(s["paneUp"], [[True]], "each pane document's pointerup, capture phase, ends the press")

    def test_the_escape_chain_asks_the_banner_before_the_shortcuts_dialog(self):
        # executed, not read: the shortcuts dialog's close is stubbed to claim every Escape, so the order
        # of the two branches decides who gets it. Armed, the banner takes Escape and the dialog is not
        # asked; plain, the dialog is next (its stub claims the press)
        s = run_banner("""
var KEYS = 0; window.__rompKeysClose = function () { KEYS++; return true; };
GO.onclick(); await tick(); await tick(); emit('keydown', key('Escape')); var armedEsc = { armed: state().armed, keys: KEYS, prevented: PREVENTED };
emit('keydown', key('Escape')); var plainEsc = { armed: state().armed, keys: KEYS, prevented: PREVENTED };
out({ armedEsc: armedEsc, plainEsc: plainEsc });""")
        self.assertEqual((s["armedEsc"]["armed"], s["armedEsc"]["keys"], s["armedEsc"]["prevented"]), (False, 0, 1),
                         "Escape ended the armed state; the dialog was not asked")
        self.assertEqual((s["plainEsc"]["armed"], s["plainEsc"]["keys"], s["plainEsc"]["prevented"]), (False, 1, 2),
                         "with the banner plain, the dialog is asked next")

    def test_escape_disarms_through_the_shells_escape_chain(self):
        # the shell's Escape chain (_LANDING_ESC_JS, run here too) asks the banner first: an armed
        # banner is what Escape closes, the keydown is claimed (default prevented, propagation stopped)
        # and focus returns to Update when it was in the banner; a plain banner leaves Escape to the
        # rest of the chain; an Escape from a pane document (focus in the frame) disarms without pulling
        # focus into the shell
        s = run_banner("""
emit('keydown', key('Escape')); var plain = state();
GO.onclick(); await tick(); emit('keydown', key('Escape')); var escaped = state();
emit('keydown', key('Enter')); GO.onclick(); var rearmed = state(); await tick();
document.activeElement = IFRAME; emit('keydown', key('Escape')); var fromPane = state();
out({ plain: plain, escaped: escaped, rearmed: rearmed, fromPane: fromPane, hook: typeof window.__rompUpdDisarm });""")
        self.assertEqual(s["hook"], "function")
        self.assertEqual((s["plain"]["armed"], s["plain"]["prevented"], s["plain"]["stopped"]), (False, 0, 0),
                         "nothing armed: Escape is not claimed")
        e = s["escaped"]
        self.assertEqual((e["armed"], e["go"], e["labelHidden"], e["cancelHidden"], e["shown"], e["posts"]),
                         (False, "Update", True, True, True, []), "Escape ended the armed state and kept the offer")
        self.assertEqual((e["prevented"], e["stopped"], e["active"]), (1, 1, "rupd-go"), "claimed, and focus back on Update")
        self.assertEqual((s["rearmed"]["armed"], s["rearmed"]["posts"]), (True, []), "an activation after Escape arms again, never posts")
        f = s["fromPane"]
        self.assertEqual((f["armed"], f["active"], f["prevented"]), (False, "pane-frame", 2), "disarmed; focus stays in the pane")

    def test_a_press_or_a_focus_inside_a_pane_disarms_through_the_panes_own_document_and_window(self):
        # a press in a pane never reaches the shell document, and in Firefox fires neither the shell
        # window's blur nor a focusout (the Browser leg below measures that), so the banner wires each
        # pane document's own pointerdown and its window's focus, capture phase, once: at load, on the
        # frame's (re)load (a pane that reloads while armed gets a fresh document), and at every arm (a
        # frame added since the page loaded)
        s = run_banner("""
var wired = state(); GO.onclick(); await tick(); eemit(PANE.contentDocument, 'pointerdown'); var pressed = state();
GO.onclick(); await tick(); eemit(PANE.contentDocument.defaultView, 'focus'); var focused = state();
PANE.contentDocument = paneDoc(); eemit(PANE, 'load');                       // the pane reloaded
GO.onclick(); await tick(); var rearmed = state(); eemit(PANE.contentDocument, 'pointerdown'); var pressed2 = state();
var LATE = frame('f-late'); FRAMES.push(LATE); var added = state();          // a frame added since the page loaded
GO.onclick(); await tick(); var armed3 = state(); eemit(LATE.contentDocument, 'pointerdown'); var pressed3 = state();
out({ wired: wired, pressed: pressed, focused: focused, rearmed: rearmed, pressed2: pressed2, added: added, armed3: armed3, pressed3: pressed3 });""")
        self.assertEqual((s["wired"]["paneWired"], s["wired"]["paneFocus"], s["wired"]["paneLoad"]), ([[True]], [[True]], [1]),
                         "wired at load, capture phase, document press and window focus, with one load handler on the frame")
        self.assertEqual((s["pressed"]["armed"], s["pressed"]["go"]), (False, "Update"), "a press in the pane disarms")
        self.assertEqual((s["focused"]["armed"], s["focused"]["active"]), (False, "rupd-armed"),
                         "focus entering the pane window disarms, without pulling focus back")
        self.assertEqual((s["rearmed"]["paneWired"], s["rearmed"]["paneFocus"]), ([[True]], [[True]]),
                         "the reloaded pane's new document is wired once (load and arm do not stack)")
        self.assertEqual(s["rearmed"]["paneLoad"], [1], "and the frame keeps its one load handler")
        self.assertFalse(s["pressed2"]["armed"], "a press in the reloaded pane disarms")
        self.assertEqual(s["added"]["paneWired"], [[True], []], "a frame added later is not wired yet")
        self.assertEqual((s["armed3"]["paneWired"], s["armed3"]["paneLoad"]), ([[True], [True]], [1, 1]), "the arm wires it")
        self.assertFalse(s["pressed3"]["armed"])
        for k in ("pressed", "focused", "pressed2", "pressed3"):
            self.assertEqual(s[k]["posts"], [], k)

    def test_a_pane_still_parsing_is_wired_at_once_and_not_twice_at_its_load(self):
        # a document whose readyState is loading is the document that finishes loading, so it is wired
        # like any other: a press in it during the parse disarms (a skip left the pane unwired until its
        # load, and a press there on a control that cancels mousedown kept the armed state); its load
        # then finds it wired and adds nothing
        s = run_banner("""
var LOADING = frame('f-slow', 'loading'); FRAMES.push(LOADING);
GO.onclick(); await tick(); var armed1 = state(); eemit(LOADING.contentDocument, 'pointerdown'); var pressed = state();
CF.onclick(); var noPost = state();
LOADING.contentDocument.readyState = 'complete'; eemit(LOADING, 'load'); var loaded = state();
GO.onclick(); await tick(); var rearmed = state(); eemit(LOADING.contentDocument.defaultView, 'focus'); var focused = state();
out({ armed1: armed1, pressed: pressed, noPost: noPost, loaded: loaded, rearmed: rearmed, focused: focused });""")
        self.assertEqual((s["armed1"]["armed"], s["armed1"]["paneWired"], s["armed1"]["paneFocus"]), (True, [[True], [True]], [[True], [True]]),
                         "the parsing pane is wired at the arm")
        self.assertEqual((s["pressed"]["armed"], s["pressed"]["posts"]), (False, []), "a press in it during the parse disarms")
        self.assertEqual(s["noPost"]["posts"], [], "and the confirm, no longer armed, posts nothing")
        self.assertEqual((s["loaded"]["paneWired"], s["loaded"]["paneFocus"], s["loaded"]["paneLoad"]), ([[True], [True]], [[True], [True]], [1, 1]),
                         "its load adds no second listener")
        self.assertEqual((s["rearmed"]["armed"], s["focused"]["armed"]), (True, False))

    def test_the_click_that_focuses_the_window_never_posts(self):
        # the incident's shape: the banner was left armed, focus went to another window (blur), and the
        # click that brought focus back landed on the banner. The blur disarmed it, so that click finds a
        # plain Update and arms it; nothing is posted
        s = run_banner("""
GO.onclick(); await tick(); wemit('blur'); var away = state();
GO.onclick(); var back = state(); await tick(); await tick();
out({ away: away, back: back, settled: state() });""")
        self.assertEqual((s["away"]["armed"], s["away"]["go"]), (False, "Update"))
        self.assertEqual((s["back"]["armed"], s["back"]["posts"]), (True, []), "the focusing click arms, never posts")
        self.assertEqual(s["settled"]["posts"], [])

    def test_a_refused_post_re_offers_without_the_armed_state(self):
        # the kernel's refusal of an unconfirmed body (a page that predates the confirm step) reaches
        # the banner as the existing error text and re-offers a plain Update
        s = run_banner("""
UPDATE_OK = false; UPDATE_TEXT = "the update starts only from a confirmed click on the banner";
GO.onclick(); await tick(); await tick(); CF.onclick(); await tick(); await tick(); await tick();
out(state());""")
        self.assertEqual(len(s["posts"]), 1)
        self.assertTrue(s["msg"].startswith("Could not start the update: the update starts only from a confirmed click"))
        self.assertEqual((s["armed"], s["go"], s["goDisabled"], s["notNowHidden"]), (False, "Update", False, False))


class Wiring(unittest.TestCase):
    """Source pins on the parts node does not execute: the markup, the stylesheet, the Escape chain's
    order and the kernel route."""

    def test_the_markup_carries_the_armed_row_hidden_and_the_post_carries_the_confirmation(self):
        html = km._UPD_HTML
        self.assertIn("<button class=rup-dismiss id=rupd-dismiss>Not now</button>", html)
        self.assertIn("<button class=rup-cancel id=rupd-cancel hidden>Cancel</button>", html)
        self.assertIn("<button class=rup-go id=rupd-go>Update</button>", html)
        self.assertIn("<span class=rup-armed id=rupd-armed tabindex=-1 hidden></span>", html)
        self.assertIn("<button class=rup-confirm id=rupd-confirm hidden>Restart</button>", html)
        order = [html.index(i) for i in ("rup-msg", "rupd-dismiss", "rupd-cancel", "rupd-go", "rupd-armed", "rupd-confirm")]
        self.assertEqual(order, sorted(order), "the plain row reads Not now, Update; the armed row Cancel, label, Restart, in one flow")
        js = km._UPD_JS
        self.assertIn("body:JSON.stringify({confirmed:true})", js)
        self.assertIn("go.onclick=function(){if(!armed)arm();};", js, "Update only ever arms")
        self.assertIn("cf.onclick=function(e){if(!armed)return;if(e&&e.detail>1)return;", js, "the confirm posts, the click-count guard kept")
        self.assertIn("function noRepeat(e){if(e&&e.repeat&&(e.key==='Enter'||e.key===' '))e.preventDefault();}", js)
        self.assertIn("go.addEventListener('keydown',noRepeat);cf.addEventListener('keydown',noRepeat);", js)

    def test_the_armed_state_ends_on_events_never_a_timer(self):
        js = km._UPD_JS
        for ev in ("cx.onclick=function(){disarm(true,true);};",
                   "window.__rompUpdDisarm=function(){if(!armed)return false;disarm(true);return true;};",
                   "d.addEventListener('pointerdown',function(){if(armed)disarm();},true);",
                   "d.addEventListener('pointerup',function(){press=false;},true);",
                   "var w=d.defaultView;if(w)w.addEventListener('focus',function(){if(armed)disarm();},true);}catch(e){}}",
                   "box.classList.add('rup-arm');fit(g);wireFrames();",
                   "function disarm(back,always){if(!armed)return;var a=document.activeElement,inside=back&&(always||(a&&box.contains(a)));",
                   "armed=false;window.removeEventListener('resize',refit);",
                   "document.addEventListener('pointerdown',function(e){var inside=!!(e&&e.target&&box.contains(e.target));press=inside&&e.button===0&&e.isPrimary!==false;if(armed&&!inside)disarm();},true);",
                   "document.addEventListener('pointerup',function(e){if(!(e&&e.target&&box.contains(e.target)))press=false;},true);",
                   "document.addEventListener('pointerleave',function(e){if(e&&e.pointerType==='mouse'&&!(e.target&&box.contains(e.target)))press=false;},true);",
                   "document.addEventListener('click',function(){press=false;},true);",
                   "document.addEventListener('pointercancel',function(){press=false;},true);",
                   "box.addEventListener('focusout',function(e){if(!armed)return;var t=e&&e.relatedTarget;if(t&&box.contains(t))return;if(!t&&press)return;disarm();});",
                   "window.addEventListener('blur',function(){press=false;disarm();});",
                   "document.addEventListener('visibilitychange',function(){if(document.hidden)disarm();});",
                   "function show(m){disarm();"):
            self.assertIn(ev, js)
        self.assertNotIn("readyState", js, "a parsing pane document is wired like any other, never skipped")
        # the press ends at a pointerup OUTSIDE the box only, and at a MOUSE pointer's leave outside it: a
        # tap's pointerup inside the box, its lostpointercapture and its leave chain up to the root all come
        # before the compatibility mousedown that moves focus (the executed cases above play that order)
        self.assertEqual(js.count("'pointerup'"), 2, "the shell document's guarded clear and the pane document's")
        self.assertNotIn("lostpointercapture", js, "released between a tap's pointerup and its compat mousedown, so never an ending")
        self.assertNotIn("'mouseup'", js)
        # the only timers in the WHOLE served script are the in-flight poll's two setTimeout(poll,3000)
        # calls, and no other clock: a new listener that disarmed on a timer, or a setInterval, adds a call
        # and fails this
        self.assertEqual(re.findall(r"set(?:Timeout|Interval)\([^)]*\)", js), ["setTimeout(poll,3000)"] * 2)
        for banned in ("requestAnimationFrame", "requestIdleCallback", "Date.now", "performance.now"):
            self.assertNotIn(banned, js)

    def test_the_shells_escape_chain_asks_the_banner_first(self):
        esc = km._LANDING_ESC_JS
        self.assertIn("if(window.__rompUpdDisarm&&window.__rompUpdDisarm()){closed=true;}\nelse if(window.__rompKeysClose", esc)
        self.assertLess(esc.index("__rompUpdDisarm"), esc.index("__rompKeysClose"), "the banner sits over every panel")

    def test_the_armed_red_is_the_error_token_the_shell_defines_for_both_themes(self):
        # ui/CLAUDE.md: a hex only as a var() fallback. The shell loads no sheet, so it defines --err
        # inline, in both themes, and the confirm's rule reads it
        css = km._UPD_CSS
        self.assertIn("#rupd .rup-confirm{background:var(--err,#c0392b);", css)
        self.assertNotIn("rup-confirm{background:#", css, "never the bare hex")
        self.assertIn("#rupd.rup-arm .rup-go{display:none}", css, "the armed class hides Update; its own hidden flag stays the offer's")
        self.assertIn("#rupd .rup-armed{font-weight:500;user-select:none;-webkit-user-select:none}", css,
                      "the double-click the layout routes onto the label paints no selection")
        self.assertIn("border-color:rgba(0,0,0,0.25);margin-left:12px}", css, "the confirm's margin: with the box's gap, 24px past the label")
        self.assertIn("#rupd.rup-arm .rup-armed{display:flex;align-items:center;align-self:stretch;padding:6px 0}", css,
                      "the label is as tall as a button and the row, under the armed class only so hidden still hides it")
        js = km._UPD_JS
        self.assertIn("function arm(){var t=label(),g=rect(go);", js, "Update's footprint is measured before it hides")
        self.assertIn("box.classList.add('rup-arm');fit(g);wireFrames();", js)
        self.assertIn("var w=Math.max(l.width,g.width),d=g.right-l.right;if(d>0)w=Math.max(w,l.width+2*d);", js,
                      "at least Update's width, and wide enough that its right edge reaches Update's")
        html = km._landing()
        html = html if isinstance(html, str) else html.decode("utf-8")
        self.assertIn(":root{--err:#c0392b}", html)
        self.assertIn("body.theme-light{--err:#B02A1C}", html)

    def test_the_box_sizes_to_its_content_and_wraps_inside_the_viewport(self):
        # a fixed box with left:50% shrink-to-fit against the half viewport: a long armed label wrapped
        # the message on a desktop and pushed Cancel past a phone's edge. max-content sizing, wrap, and
        # the sibling banner's phone rule, where the armed label takes a full row of its own so the
        # confirm never sits on the row where Update was (the Browser leg below measures the widths)
        css = km._UPD_CSS
        self.assertIn("z-index:99999;display:none;flex-wrap:wrap;width:max-content;align-items:center;gap:12px;"
                      "max-width:92vw;box-sizing:border-box;", css)
        self.assertIn("@media (max-width:640px){#rupd{width:92vw;gap:10px 12px}"
                      "#rupd .rup-msg,#rupd .rup-armed{flex:1 1 100%}#rupd button{flex:1 1 auto;white-space:normal}"
                      "#rupd .rup-cancel,#rupd .rup-confirm{order:1}}", css,
                      "on a phone Cancel and the confirm share the row beneath the label, never the row Not now and Update had")
        self.assertIn("#rupd .rup-confirm:hover:not(:disabled){background:var(--err,#c0392b);", css,
                      "the confirm's hover restates the red")

    def test_the_route_refuses_a_body_without_the_confirmation_before_reading_any_check(self):
        # the executed version (a check that raises when read) is in tests/test_kernel_update.py; this
        # pins the shape and that both doors audit the confirmation
        src = km_src()
        route = src[src.index('if u.path == "/update":'):src.index('if u.path == "/notify-all":')]
        self.assertIn('if b.get("confirmed") is not True:', route)
        self.assertLess(route.index('if b.get("confirmed") is not True:'), route.index("tag = _UPDATE_AVAIL[0]"),
                        "refused before the kernel's own checks are read")
        self.assertEqual(route.count('via="update-confirmed"'), 2, "both doors the click can take audit the confirmation")


def km_src():
    with open(os.path.join(BIN, "romp-kernel"), encoding="utf-8") as f:
        return f.read()


# ── real engines ──────────────────────────────────────────────────────────────────────────────────
# The served CSS, markup and script, with the shell's Escape chain, on a scratch page beside a same-origin
# iframe (a pane), driven with real input in Playwright's Chromium and Firefox. The page's --err token is
# the shell's own line, lifted from _landing(). /update-check, /update and /update-dismiss are answered by
# the driver, which counts the posts and the dismissals. The context has touch, for the two-taps step.
DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const pw = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await pw[cfg.engine].launch(cfg.launch || {}); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const R = { engine: cfg.engine, leg: cfg.leg, err: {}, pageErrors: [] };
const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, hasTouch: true });
const page = await ctx.newPage();
page.on("pageerror", (e) => { R.pageErrors.push(String((e && e.message) || e)); });
let posts = 0, dismisses = 0, check = cfg.checks.std;
await page.route("http://romp.test/**", (route) => {
  const u = new URL(route.request().url());
  const html = (body) => route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body });
  if (u.pathname === "/shell") return html(cfg.page);
  if (u.pathname === "/pane") return html(cfg.pane);
  if (u.pathname === "/update-check") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(check) });
  if (u.pathname === "/update") { posts++; return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true, state: "running" }) }); }
  if (u.pathname === "/update-dismiss") { dismisses++; return route.fulfill({ status: 200, contentType: "application/json", body: "{}" }); }
  return route.fulfill({ status: 404, body: "" });
});
// `variant` picks the /update-check answer, and with it the label: std, shortest or longest
const load = async (variant) => {
  check = cfg.checks[variant || "std"];
  await page.goto("http://romp.test/shell");
  await page.waitForFunction(() => document.getElementById("rupd").classList.contains("show"), null, { timeout: 15000 });
  await page.waitForFunction(() => document.getElementById("pane").contentDocument && document.getElementById("pane").contentDocument.getElementById("pane-btn"), null, { timeout: 15000 });
  // diagnosis only: what the banner's click events looked like (target and the browser's click count)
  await page.evaluate(() => {
    window.__clicks = []; window.__cxClicks = 0;
    document.getElementById("rupd").addEventListener("click", (e) => { window.__clicks.push([(e.target && e.target.id) || e.target.tagName, e.detail]); }, true);
    document.getElementById("rupd-cancel").addEventListener("click", () => { window.__cxClicks++; });
  });
};
const st = () => page.evaluate(() => {
  const box = document.getElementById("rupd"), go = document.getElementById("rupd-go"), lbl = document.getElementById("rupd-armed"),
        cf = document.getElementById("rupd-confirm"), cx = document.getElementById("rupd-cancel"), dm = document.getElementById("rupd-dismiss"),
        msg = box.querySelector(".rup-msg");
  const r = (n) => { const b = n.getBoundingClientRect(); return { left: b.left, right: b.right, top: b.top, bottom: b.bottom, width: b.width, height: b.height }; };
  const a = document.activeElement;
  const cs = getComputedStyle(lbl);
  return { armed: box.classList.contains("rup-arm"), shown: box.classList.contains("show"), go: go.textContent, label: lbl.textContent,
           goVisible: go.getClientRects().length > 0, labelHidden: lbl.hidden, confirmHidden: cf.hidden, cancelHidden: cx.hidden,
           notNowHidden: dm.hidden, goDisabled: go.disabled,
           active: a ? (a.id || a.tagName) : "", cfBg: getComputedStyle(cf).backgroundColor,
           userSelect: cs.userSelect || cs.webkitUserSelect || "", lblMinWidth: lbl.style.minWidth,
           box: r(box), goRect: r(go), lblRect: r(lbl), cf: r(cf), cx: r(cx), dm: r(dm), msg: r(msg), scrollWidth: box.scrollWidth, clientWidth: box.clientWidth,
           vw: window.innerWidth, docWidth: document.documentElement.scrollWidth,
           clicks: window.__clicks.slice(), cxClicks: window.__cxClicks };
});
const center = async (sel) => page.evaluate((s) => { const b = document.querySelector(s).getBoundingClientRect(); return { x: b.left + b.width / 2, y: b.top + b.height / 2 }; }, sel);
const settle = async (want) => { for (let i = 0; i < 100 && posts < want; i++) await new Promise((r) => setTimeout(r, 50)); return posts; };
const step = async (name, fn) => { try { R[name] = await fn(); } catch (e) { R.err[name] = String((e && e.stack) || e); } };
// the plain row's rects (Update, Not now) before the arm, then the armed row's after it
const armAt = async (w) => {
  await page.setViewportSize({ width: w, height: 800 });
  const plain = await st();
  const goPt = await center("#rupd-go");
  await page.click("#rupd-go");
  const s = await st();
  s.goPt = goPt;
  s.plain = { go: plain.goRect, dm: plain.dm, msg: plain.msg, box: plain.box };
  return s;
};

await load();
// 1. widths (the standard label): armed at a phone width, the label and Cancel stay inside the viewport; a
// desktop keeps one row; at every width the confirm is never where Update was, the red resolves through
// the token under the pointer, and a REAL click on Cancel disarms
await step("widths", async () => {
  const out = {};
  for (const w of [390, 360, 700, 1000, 1280]) {
    const s = await armAt(w);
    await page.hover("#rupd-confirm"); s.cfBgHover = (await st()).cfBg;
    await page.mouse.move(5, 790);
    const p0 = posts, d0 = dismisses, c0 = s.cxClicks;
    await page.click("#rupd-cancel");
    s.afterCancel = await st(); s.afterCancel.posts = posts - p0; s.afterCancel.dismisses = dismisses - d0; s.afterCancel.cxClicks -= c0;
    out[w] = s;
  }
  await page.setViewportSize({ width: 1280, height: 800 });
  return out;
});
// 1b. the armed row's geometry against the plain row's with the shortest and the longest label, at the
// five widths (Escape disarms between widths)
await step("geometry", async () => {
  const out = {};
  for (const variant of ["shortest", "longest"]) {
    await load(variant);
    out[variant] = {};
    for (const w of [390, 360, 700, 1000, 1280]) {
      out[variant][w] = await armAt(w);
      await page.keyboard.press("Escape");
    }
  }
  await page.setViewportSize({ width: 1280, height: 800 });
  return out;
});
// 1e. the re-read shrinks the label: the page holds the standard label, the kernel now answers the
// shortest; the answer is held until the fitted standard label is measured, then released, and the
// shortest label must still cover Update's footprint with Restart 24 px past its right edge; a spread
// two-tap (2 px inside Update's right edge, then 8 px further right) then posts nothing
await step("reread", async () => {
  const out = {};
  for (const w of [1280, 700]) {
    await load();
    await page.setViewportSize({ width: w, height: 800 });
    const plain = await st();
    let release; hold = new Promise((r) => { release = r; });
    check = cfg.checks.shortest;
    await page.click("#rupd-go");
    const held = await st();
    release(); hold = null;
    await page.waitForFunction((t) => document.getElementById("rupd-armed").textContent === t, cfg.labels.shortest, { timeout: 15000 });
    const after = await st();
    held.plain = after.plain = plainOf(plain);
    const before = posts;
    await page.evaluate(() => { window.__clicks = []; });
    const g = plain.goRect, y = g.top + g.height / 2;
    await page.touchscreen.tap(g.right - 2, y);
    await page.touchscreen.tap(g.right + 6, y);
    const p = await settle(before + 1);
    out[w] = { held, after, posts: p - before, clicks: (await st()).clicks };
    await page.keyboard.press("Escape");
    check = cfg.checks.std;
  }
  await page.setViewportSize({ width: 1280, height: 800 });
  return out;
});
// 1f. how a press that began inside the banner ends: a primary press on the label released over the pane
// iframe, one released outside the viewport, a right click on the label, a middle click on Restart and a
// right click on the message text. After each, a script blur of whatever is focused: a focusout to
// nothing, which disarms unless a press is still recorded
await step("pressEnds", async () => {
  const out = {};
  const probe = async (name, fn) => {
    await load();
    await page.click("#rupd-go");
    await fn();
    const mid = await st();
    const blurred = await page.evaluate(() => { const a = document.activeElement; if (a && a.blur) a.blur(); return a ? (a.id || a.tagName) : ""; });
    const after = await st();
    await page.mouse.click(5, 790);                    // a press elsewhere: the recovery from a flag that outlived its gesture
    out[name] = { mid, blurred, after, recovered: await st(), posts };
  };
  const lblCenter = () => center("#rupd-armed");
  await probe("intoPane", async () => {
    const p = await lblCenter(); const pb = await page.frameLocator("#pane").locator("#pane-body").boundingBox();
    await page.mouse.move(p.x, p.y); await page.mouse.down(); await page.mouse.move(pb.x + 30, pb.y + 30, { steps: 6 }); await page.mouse.up();
  });
  await probe("outsideRight", async () => {          // past the right edge, level with the banner: the pointer leaves the box and then the window
    const p = await lblCenter();
    await page.mouse.move(p.x, p.y); await page.mouse.down(); await page.mouse.move(1350, p.y, { steps: 6 }); await page.mouse.up();
  });
  await probe("outsideTop", async () => {            // past the top edge: the pointer crosses the body above the banner and leaves it
    const p = await lblCenter();
    await page.mouse.move(p.x, p.y); await page.mouse.down(); await page.mouse.move(p.x, -40, { steps: 6 }); await page.mouse.up();
  });
  await probe("rightLabel", async () => { await page.click("#rupd-armed", { button: "right" }); });
  await probe("middleRestart", async () => { await page.click("#rupd-confirm", { button: "middle" }); });
  await probe("rightMessage", async () => { await page.click("#rupd .rup-msg", { button: "right" }); });
  return out;
});
// 1c. a spread double-tap with the shortest label: a tap 2 px inside Update's right edge, then one 8 px
// further right; the second must land on the label or the gap, never on the confirm
await step("spreadTaps", async () => {
  const out = {};
  await load("shortest");
  for (const w of [700, 1000, 1280]) {
    await page.setViewportSize({ width: w, height: 800 });
    await page.evaluate(() => { window.__clicks = []; });
    const plainGo = (await st()).goRect;
    const b = { right: plainGo.right, y: plainGo.top + plainGo.height / 2 };
    const before = posts;
    await page.touchscreen.tap(b.right - 2, b.y);
    await page.touchscreen.tap(b.right + 6, b.y);
    const s = await st();
    const p = await settle(before + 1);
    out[w] = { armed: s.armed, clicks: s.clicks, posts: p - before, active: s.active, cf: s.cf, lbl: s.lblRect, plainGo };
    await page.keyboard.press("Escape");
  }
  await page.setViewportSize({ width: 1280, height: 800 });
  return out;
});
// 1d. a click on the banner's own message text keeps the armed state, and a drag still selects the text
await step("textPress", async () => {
  await load();
  await page.click("#rupd-go");
  await page.click("#rupd .rup-msg");
  const afterClick = await st();
  const m = await page.evaluate(() => { const r = document.querySelector("#rupd .rup-msg").getBoundingClientRect(); return { l: r.left + 4, r: r.right - 4, y: r.top + r.height / 2 }; });
  await page.mouse.move(m.l, m.y); await page.mouse.down(); await page.mouse.move(m.r, m.y, { steps: 5 }); await page.mouse.up();
  const afterDrag = await st();
  const selected = await page.evaluate(() => String(window.getSelection()).length);
  await page.keyboard.press("Escape");
  return { afterClick, afterDrag, selected, posts };
});
// 2. a press inside the pane iframe disarms (the pane document's own pointerdown; Chromium also blurs the top window)
await load();
await step("pane", async () => {
  await page.click("#rupd-go");
  const armed = await st();
  await page.frameLocator("#pane").locator("#pane-body").click();
  const after = await st();
  return { armed, after, posts };
});
// 3. a double-click arms and posts nothing (the second click lands on the label); a click on the confirm posts once
await load();
await step("dbl", async () => {
  const before = posts;
  await page.dblclick("#rupd-go");
  const afterDbl = await st();
  const postsDbl = await settle(before + 1);          // give a stray post every chance to land: none may
  await page.click("#rupd-confirm");
  const postsConfirm = await settle(before + 1);
  return { afterDbl, postsDbl: postsDbl - before, postsConfirm: postsConfirm - before, after: await st() };
});
// 3b. a touch tap on the confirm posts once: the touch order (pointerup before the compatibility mousedown
// that moves focus) is the one the press flag must outlive
await load();
await step("tapRestart", async () => {
  const before = posts;
  const pt = await center("#rupd-go");
  await page.touchscreen.tap(pt.x, pt.y);
  const armed = await st();
  const c = await center("#rupd-confirm");
  await page.touchscreen.tap(c.x, c.y);
  const p = await settle(before + 1);
  return { armed, posts: p - before, after: await st() };
});
// 4. a held Enter on the focused Update button: the first keydown arms, the repeat (repeat:true) lands
// on the label and posts nothing; Enter on the focused confirm posts once
await load();
await step("heldEnter", async () => {
  const before = posts;
  await page.focus("#rupd-go");
  await page.keyboard.down("Enter");
  await page.keyboard.down("Enter");                  // the same key again: Playwright sets repeat on it
  await page.keyboard.down("Enter");
  await page.keyboard.up("Enter");
  const afterHold = await st();
  const postsHold = await settle(before + 1);
  await page.focus("#rupd-confirm");
  await page.keyboard.press("Enter");
  const postsEnter = await settle(before + 1);
  return { afterHold, postsHold: postsHold - before, postsEnter: postsEnter - before, after: await st() };
});
// 5. two taps at the Update button's point (a touch double-tap): the second lands on the label; nothing posts
await load();
await step("taps", async () => {
  const before = posts;
  const pt = await center("#rupd-go");
  await page.touchscreen.tap(pt.x, pt.y);
  await page.touchscreen.tap(pt.x, pt.y);
  const after = await st();
  const postsTaps = await settle(before + 1);
  return { after, postsTaps: postsTaps - before };
});
// 6. Tab from the armed state reaches the confirm without disarming; Shift+Tab from it reaches Cancel (it
// stands before the label, where Not now stood; the label, tabindex -1, is not in the Tab order); Enter
// on Cancel disarms
await load();
await step("tab", async () => {
  const before = posts;
  await page.click("#rupd-go");
  const armed = await st();
  await page.keyboard.press("Tab");
  const onConfirm = await st();
  await page.keyboard.press("Shift+Tab");
  const onCancel = await st();
  await page.keyboard.press("Enter");
  const after = await st();
  const postsAfter = await settle(before + 1);
  return { armed, onConfirm, onCancel, after, posts: postsAfter - before, dismisses };
});
// 7. Escape disarms through the shell's chain; Enter afterwards (focus back on Update) arms again, no post
await step("escape", async () => {
  const before = posts;
  await page.click("#rupd-go");
  const armed = await st();
  await page.keyboard.press("Escape");
  const afterEsc = await st();
  await page.keyboard.press("Enter");
  const afterEnter = await st();
  const postsAfter = await settle(before + 1);
  await page.keyboard.press("Escape");
  return { armed, afterEsc, afterEnter, posts: postsAfter - before };
});
// 8. Tab from the confirm into the pane: focus enters the frame (no focusout in Firefox); the pane window's focus disarms
await step("tabIntoPane", async () => {
  const before = posts;
  await page.click("#rupd-go");
  await page.keyboard.press("Tab");
  const onConfirm = await st();
  await page.keyboard.press("Tab");
  const after = await st();
  // where focus landed inside the frame: Chromium's first Tab into a frame reaches its first control,
  // Firefox's reaches the frame's document (its body) and the next Tab the control
  const paneActive = await page.frameLocator("#pane").locator("body").evaluate((b) => (b.ownerDocument.activeElement || {}).id || "");
  return { onConfirm, after, paneActive, posts: posts - before };
});
await browser.close();
process.stdout.write("RESULT:" + JSON.stringify(R) + "\n");
process.exit(0);
"""


def _scratch_page():
    """The shell's --err line, the banner's CSS, markup and script, the shell's Escape chain, and a pane
    iframe below the banner."""
    html = km._landing()
    html = html if isinstance(html, str) else html.decode("utf-8")
    tok = re.search(r":root\{--err:#[0-9a-fA-F]{6}\}", html)     # Wiring pins that it exists; without it
    #                                                                   the confirm's var() fallback paints
    return ("<!DOCTYPE html><html><head><meta charset=utf-8><style>" + (tok.group(0) if tok else "") + km._UPD_CSS
            + "iframe#pane{position:fixed;top:220px;left:20px;width:300px;height:300px;border:1px solid #888}"
            + "body{margin:0;min-height:100vh}"        # the shell's body spans the viewport: a pointer leaving it has left the window
            + "</style></head><body>" + km._UPD_HTML
            + "<iframe id=pane src=/pane></iframe><script>" + km._LANDING_ESC_JS + "</script><script>" + km._UPD_JS
            + "</script></body></html>")


PANE = ("<!DOCTYPE html><html><head><meta charset=utf-8></head><body id=pane-body style='margin:0;height:300px'>"
        "pane <button id=pane-btn style='margin-top:120px'>in the pane</button></body></html>")
CHECK = {"cur": "v0.1.0", "tag": "v0.2.0", "mode": "ask", "state": "", "boot": "b1", "drift": "", "driftSha": "",
         "sessions": 32, "midTurn": 3, "otherKernels": 0}       # the long label, the width case that overflowed
# the three labels the geometry is measured with: the standard one, the shortest form the script can
# produce (one session, nothing interrupted, one kernel) and the longest (the manager did not answer)
CHECKS = {"std": CHECK,
          "shortest": dict(CHECK, sessions=1, midTurn=0),
          "longest": dict(CHECK, sessions=32, midTurn=3, otherKernels=None)}
LABELS = {"std": "Restart 32 sessions now, interrupting 3",
          "shortest": "Restart 1 session now",
          "longest": "Restart 32 sessions here now, interrupting 3; the other kernels may restart too (the manager did not answer)"}
LABEL = LABELS["std"]


def _contains(rect, pt):
    return rect["left"] <= pt["x"] <= rect["right"] and rect["top"] <= pt["y"] <= rect["bottom"]


def _disjoint(a, b):
    """No pixel in common (a hidden element's zero rect is disjoint from everything)."""
    return (a["right"] <= b["left"] or b["right"] <= a["left"] or a["bottom"] <= b["top"] or b["bottom"] <= a["top"]
            or not a["width"] or not b["width"])


def _covers(a, b, tol=0.5):
    """b lies inside a, to half a pixel (engines round the rects differently)."""
    return (a["left"] <= b["left"] + tol and a["right"] >= b["right"] - tol
            and a["top"] <= b["top"] + tol and a["bottom"] >= b["bottom"] - tol)


class Browser(unittest.TestCase):
    """One driver run per leg over the scratch page; each test reads one facet per leg that ran. Skips
    loudly without playwright or a browser (CI installs none); a leg that fails to launch skips its own
    run and the *_ran tests say so. Four legs: Chromium, Firefox and WebKit as installed, and Firefox
    under Gecko's own switch for the WebKit focus rule (a press does not focus a button, so the mousedown
    on the confirm or Cancel blurs the armed label to nothing before the click: the value macOS Firefox
    shipped until 2021 and Safari's rule to this day; Playwright's Linux WebKit is the GTK port, which
    focuses buttons on a press and does not show it). The pref is an int32: a bool aborts the launch."""
    LEGS = (("chromium", "chromium", {}),
            ("firefox", "firefox", {}),
            ("webkit", "webkit", {}),
            ("firefox-mousefocus0", "firefox", {"firefoxUserPrefs": {"accessibility.mouse_focuses_formcontrol": 0}}))
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the browser legs need playwright")
        cls.R, cls.skipped = {}, {}
        lab = tempfile.mkdtemp(prefix="upd-banner-browser-")
        driver = os.path.join(lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        page = _scratch_page()
        for leg, engine, launch in cls.LEGS:
            cfg = os.path.join(lab, leg + ".json")
            with open(cfg, "w") as f:
                json.dump({"leg": leg, "engine": engine, "launch": launch, "page": page, "pane": PANE, "checks": CHECKS}, f)
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=600,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
            if p.returncode == 3:
                cls.skipped[leg] = "no playwright %s on this box (CI installs none): %s" % (engine, p.stderr.strip()[:200])
                continue
            if p.returncode != 0:
                raise AssertionError("%s driver failed:\n%s%s" % (leg, p.stdout[-3000:], p.stderr[-3000:]))
            line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
            if line is None:
                raise AssertionError("%s driver printed no result:\n%s%s" % (leg, p.stdout[-3000:], p.stderr[-3000:]))
            cls.R[leg] = json.loads(line[len("RESULT:"):])
        shutil.rmtree(lab, ignore_errors=True)
        if not cls.R:
            raise unittest.SkipTest("; ".join(cls.skipped.values()))

    def test_the_driver_hit_no_script_error(self):
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                self.assertEqual((r["err"], r["pageErrors"]), ({}, []), engine)

    def test_firefox_ran(self):
        # the pane and the Tab-into-pane cases are Firefox's: a press in a same-origin frame fires no top-window
        # blur there, and a Tab out of the banner into a frame no focusout
        if "firefox" in self.skipped:
            self.skipTest(self.skipped["firefox"])
        self.assertIn("firefox", self.R)

    def test_webkit_ran(self):
        # the third engine; its Linux port focuses buttons on a press, so the WebKit focus rule itself is
        # measured through the Gecko switch leg, not here
        if "webkit" in self.skipped:
            self.skipTest(self.skipped["webkit"])
        self.assertIn("webkit", self.R)

    def test_the_gecko_switch_for_the_webkit_focus_rule_ran(self):
        # the leg where a press does not focus a button: the confirm and Cancel cases below are red on it
        # without the press flag (the label's focusout to nothing disarmed under the mousedown)
        if "firefox-mousefocus0" in self.skipped:
            self.skipTest(self.skipped["firefox-mousefocus0"])
        self.assertIn("firefox-mousefocus0", self.R)

    def test_a_press_inside_a_pane_iframe_disarms(self):
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                p = r["pane"]
                self.assertEqual((p["armed"]["armed"], p["armed"]["active"]), (True, "rupd-armed"),
                                 engine + ": the first click armed and put focus on the label")
                self.assertFalse(p["after"]["armed"], engine + ": a press in the pane disarmed it (state: %r)" % p["after"])
                self.assertEqual((p["after"]["labelHidden"], p["after"]["cancelHidden"], p["after"]["goVisible"]), (True, True, True), engine)
                self.assertEqual(p["posts"], 0, engine)

    def test_a_double_click_posts_nothing_and_a_click_on_the_confirm_posts_once(self):
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                d = r["dbl"]
                self.assertEqual((d["postsDbl"], d["afterDbl"]["armed"]), (0, True),
                                 engine + ": the double-click armed and posted nothing (state: %r)" % d["afterDbl"])
                self.assertEqual([c[0] for c in d["afterDbl"]["clicks"]], ["rupd-go", "rupd-armed"],
                                 engine + ": the second click landed on the label, not on a control (%r)" % d["afterDbl"]["clicks"])
                self.assertEqual(d["postsConfirm"], 1, engine + ": a click on the confirm posted once")
                self.assertTrue(d["after"]["goDisabled"], engine + ": and the Update button came back disabled under the wait")

    def test_a_touch_tap_on_the_confirm_posts_once(self):
        # the touch order: pointerup before the compatibility mousedown that moves focus. Where a press does
        # not focus a button (the Gecko switch leg) the label blurs to nothing under that mousedown, after
        # pointerup; the press flag outlives pointerup, so the tap's click reaches the confirm
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                t = r["tapRestart"]
                self.assertEqual((t["armed"]["armed"], t["posts"]), (True, 1), (engine, t))

    def test_a_held_enter_arms_and_posts_nothing_and_enter_on_the_focused_confirm_posts_once(self):
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                h = r["heldEnter"]
                self.assertEqual((h["postsHold"], h["afterHold"]["armed"], h["afterHold"]["active"]), (0, True, "rupd-armed"),
                                 engine + ": the held Enter armed, its repeats landed on the label (state: %r)" % h["afterHold"])
                self.assertEqual(h["postsEnter"], 1, engine + ": Enter on the focused confirm posted once")

    def test_two_taps_at_the_update_buttons_point_post_nothing(self):
        # a touch double-tap: whatever click count the engine reports for the second tap (Playwright's
        # Firefox touch path reports 1), it lands on the label, which is not a control
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                t = r["taps"]
                self.assertEqual((t["postsTaps"], t["after"]["armed"]), (0, True),
                                 engine + ": two taps armed and posted nothing (clicks: %r)" % t["after"]["clicks"])
                self.assertEqual([c[0] for c in t["after"]["clicks"]], ["rupd-go", "rupd-armed"], engine)

    def test_a_spread_second_tap_past_updates_right_edge_never_reaches_the_confirm(self):
        # the shortest label at the desktop widths: a tap 2 px inside Update's right edge arms; a second
        # 8 px further right lands on the label (which reaches past that edge) or the gap before the
        # confirm, never on the confirm; nothing posts
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                for vw, s in r["spreadTaps"].items():
                    self.assertEqual((s["posts"], s["armed"]), (0, True), (engine, vw, s))
                    self.assertNotIn("rupd-confirm", [c[0] for c in s["clicks"]], (engine, vw, s["clicks"]))
                    go = s["plainGo"]
                    self.assertTrue(s["cf"]["left"] >= go["right"] + 24 - 0.5 or s["cf"]["top"] >= go["bottom"],
                                    (engine, vw, "the confirm begins 24 px past Update's right edge, or on a row below it", s))

    def test_a_click_on_the_banners_own_text_keeps_the_armed_state_and_the_text_still_selects(self):
        # a press on the message text blurs the label to nothing in every engine; it began inside the box,
        # so nothing disarms, and the text is not made unselectable to get there
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                t = r["textPress"]
                self.assertTrue(t["afterClick"]["armed"], (engine, "a click on the banner's text disarmed", t["afterClick"]))
                self.assertTrue(t["afterDrag"]["armed"], (engine, "a drag over the banner's text disarmed", t["afterDrag"]))
                self.assertGreater(t["selected"], 0, engine + ": the message text still selects")
                self.assertEqual(t["posts"], 0, engine)

    def test_a_real_click_on_cancel_disarms_and_keeps_the_offer(self):
        # where the engine focuses a button on a press, Cancel's mousedown moves focus within the banner
        # (relatedTarget inside); where it does not (the Gecko switch leg, Safari), the label blurs to
        # nothing under a press that began inside the box: kept either way, so the disarm waits for the
        # click itself: the handler runs, nothing is posted or dismissed, the offer stays shown
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                for vw, s in r["widths"].items():
                    a = s["afterCancel"]
                    self.assertEqual((a["armed"], a["shown"], a["goVisible"], a["labelHidden"], a["confirmHidden"], a["cancelHidden"], a["notNowHidden"]),
                                     (False, True, True, True, True, True, False), (engine, vw, a))
                    self.assertEqual((a["posts"], a["dismisses"]), (0, 0), (engine, vw))
                    self.assertEqual(a["cxClicks"], 1, (engine, vw, "Cancel's own click handler ran"))
                    self.assertEqual(a["active"], "rupd-go", (engine, vw, "focus back on Update"))

    def test_tab_reaches_the_confirm_and_shift_tab_reaches_cancel_and_enter_on_cancel_disarms(self):
        # the armed row's flow is Cancel, the label, the confirm: Tab from the label reaches the confirm,
        # Shift+Tab from the confirm reaches Cancel (the label, tabindex -1, is skipped by Tab), and the
        # banner stays armed throughout
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                t = r["tab"]
                self.assertEqual((t["armed"]["armed"], t["armed"]["active"]), (True, "rupd-armed"), engine)
                self.assertEqual((t["onConfirm"]["armed"], t["onConfirm"]["active"]), (True, "rupd-confirm"), engine + ": Tab to the confirm keeps the armed state")
                self.assertEqual((t["onCancel"]["armed"], t["onCancel"]["active"]), (True, "rupd-cancel"), engine + ": Shift+Tab to Cancel too")
                self.assertEqual((t["after"]["armed"], t["after"]["shown"], t["after"]["active"], t["after"]["cxClicks"]),
                                 (False, True, "rupd-go", 1), engine + ": Enter on Cancel disarmed (state: %r)" % t["after"])
                self.assertEqual((t["posts"], t["dismisses"]), (0, 0), engine)

    def test_escape_disarms_and_an_enter_afterwards_arms_again_without_posting(self):
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                e = r["escape"]
                self.assertTrue(e["armed"]["armed"], engine)
                self.assertEqual((e["afterEsc"]["armed"], e["afterEsc"]["shown"], e["afterEsc"]["active"]), (False, True, "rupd-go"),
                                 engine + ": Escape disarmed and put focus back on Update (state: %r)" % e["afterEsc"])
                self.assertEqual((e["afterEnter"]["armed"], e["posts"]), (True, 0), engine + ": Enter after Escape armed again, no post")

    def test_tab_from_the_confirm_into_the_pane_disarms(self):
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                t = r["tabIntoPane"]
                self.assertEqual((t["onConfirm"]["armed"], t["onConfirm"]["active"]), (True, "rupd-confirm"), engine)
                self.assertEqual(t["after"]["active"], "pane", engine + ": the shell's focus is on the frame")
                self.assertIn(t["paneActive"], ("pane-btn", "pane-body"), engine + ": focus went into the pane")
                self.assertFalse(t["after"]["armed"], engine + ": focus entering the pane disarmed (state: %r)" % t["after"])
                self.assertEqual(t["posts"], 0, engine)

    def test_the_confirm_is_never_where_update_was(self):
        # the structural guarantee under every layout: the point the first click landed on is never on
        # the confirm once armed, so no second activation of one gesture reaches it; on a one-row desktop
        # that point is on the label, which took Update's place
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                for vw, s in r["widths"].items():
                    self.assertTrue(s["armed"], (engine, vw))
                    self.assertFalse(_contains(s["cf"], s["goPt"]), (engine, vw, "the confirm covers the Update button's point", s["cf"], s["goPt"]))
                    self.assertFalse(s["goVisible"], (engine, vw, "Update is not shown while armed"))
                    if vw in ("1000", "1280"):
                        self.assertTrue(_contains(s["lblRect"], s["goPt"]), (engine, vw, "the label took Update's place", s["lblRect"], s["goPt"]))

    def _armed_row_holds(self, where, s):
        """The desktop geometry: the label covers Update's plain rect; Restart stands on the label's row to its
        right, 24 px past both the label's right edge and Update's; Cancel shares no pixel with Not now's plain
        rect; the row is one row (the label beside the message) and the box is inside the viewport."""
        go, dm = s["plain"]["go"], s["plain"]["dm"]
        self.assertTrue(s["armed"], where)
        self.assertTrue(go["width"] and dm["width"], where + ("the plain row was measured",))
        self.assertTrue(_covers(s["lblRect"], go), where + ("the label covers Update's plain rect", s["lblRect"], go))
        self.assertLess(s["lblRect"]["top"], s["msg"]["bottom"], where + ("the label is beside the message: one row", s["lblRect"], s["msg"]))
        cf, lbl = s["cf"], s["lblRect"]
        self.assertGreaterEqual(cf["left"], lbl["right"] + 24 - 0.5, where + ("Restart 24 px past the label", cf, lbl))
        self.assertGreaterEqual(cf["left"], go["right"] + 24 - 0.5, where + ("Restart 24 px past Update's right edge", cf, go))
        self.assertTrue(cf["top"] >= lbl["top"] - 0.5 and cf["bottom"] <= lbl["bottom"] + 0.5, where + ("Restart on the label's row", cf, lbl))
        self.assertTrue(_disjoint(s["cx"], dm), where + ("Cancel over Not now's plain rect", s["cx"], dm))
        self.assertTrue(_disjoint(s["cf"], go) and _disjoint(s["cf"], dm) and _disjoint(s["cx"], go), where + ("an armed control over a plain one", s))
        self.assertGreaterEqual(s["box"]["left"], 0, where + ("the box starts inside the viewport", s["box"]))
        self.assertLessEqual(s["box"]["right"], s["vw"], where + ("the box ends inside the viewport", s["box"], s["vw"]))
        self.assertLessEqual(s["docWidth"], s["vw"], where + ("no sideways scroll",))
        self.assertLessEqual(s["scrollWidth"], s["clientWidth"], where + ("the box does not overflow itself", s))

    def test_the_label_covers_update_and_restart_is_on_its_row_at_every_desktop_width_for_every_label(self):
        # ruling B (round 3) as the standing design (round 4): at 640, 660, 680, 700, 740, 800, 840, 1000,
        # 1280 and 1366 px, with the standard label, the shortest, the longest (two-digit counts, the
        # manager not answering) and the count-less form, the label covers Update's plain rect, Restart
        # stands to its right on Update's row and Cancel never shares a pixel with Not now: where the row
        # is short of room the label's text wraps inside it, never the row. Red before round 4 at 640 to
        # 680 (Cancel over Not now), at 740 to 840 (Restart on a row of its own) and for the longest label
        # at 1280 to 1366 (the same)
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                for variant in ("std", "shortest", "longest", "unknown"):
                    for vw in GEOM_WIDTHS:
                        s = r["geometry"][variant]["widths"][str(vw)]
                        self.assertEqual(s["label"], LABELS[variant], (engine, variant, vw))
                        self._armed_row_holds((engine, variant, vw), s)

    def test_a_resize_while_armed_re_fits_the_row(self):
        # armed at 1280 and resized to 700, then the phone width, then 1000, then 660: the geometry above
        # holds at each desktop width against the plain row the page has at that width (the arm's
        # measurement is stale after a resize: the plain row is re-measured from a hidden clone), and at
        # the phone width the label and the buttons take their rows with the desktop fit cleared
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                for variant in ("std", "shortest", "longest", "unknown"):
                    rz = r["geometry"][variant]["resize"]
                    for vw in ("700", "1000", "660"):
                        self.assertTrue(rz[vw]["armed"], (engine, variant, vw, "still armed after the resize"))
                        self._armed_row_holds((engine, variant, vw, "after a resize"), rz[vw])
                    s = rz["360"]
                    self.assertTrue(s["armed"], (engine, variant))
                    self.assertGreaterEqual(s["lblRect"]["top"], s["msg"]["bottom"], (engine, variant, "the phone rows after a resize", s))
                    self.assertGreaterEqual(s["cf"]["top"], s["lblRect"]["bottom"], (engine, variant, s))
                    self.assertEqual((s["boxTransform"], s["boxMaxWidth"], s["lblMinWidth"]), ("", "", ""), (engine, variant, "the desktop fit is cleared on the phone"))
                    self.assertLessEqual(s["docWidth"], s["vw"], (engine, variant))

    def test_the_re_read_re_fits_a_shorter_label(self):
        # the arm fitted the standard label; the re-read replaced it with the shortest. Before round 4 the
        # label shrank, stopped covering Update's footprint and Restart landed under a pixel past Update's
        # right edge, so a spread second tap posted. Now the shorter label is fitted again: it covers, Restart
        # is 24 px past, and the two taps post nothing
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                for vw, s in r["reread"].items():
                    self.assertEqual((s["held"]["label"], s["after"]["label"]), (LABELS["std"], LABELS["shortest"]), (engine, vw))
                    self._armed_row_holds((engine, vw, "the held label"), s["held"])
                    self._armed_row_holds((engine, vw, "after the re-read"), s["after"])
                    self.assertEqual((s["posts"], s["after"]["armed"]), (0, True), (engine, vw, s["clicks"]))
                    self.assertNotIn("rupd-confirm", [c[0] for c in s["clicks"]], (engine, vw, s["clicks"]))

    def test_how_a_press_that_began_inside_the_banner_ends(self):
        # the press flag must not outlive the gesture that set it. After each gesture a script blur of the
        # focused control is a focusout to nothing: it disarms when no press is recorded. A primary press
        # released over the pane (its pointerup reaches the pane document alone) ends through the pane's
        # listener; a right click on the label or a middle click on Restart never records a press; a right
        # press on the message text blurs the label to nothing at the mousedown and, with no press recorded,
        # disarms there. A primary press released outside the viewport ends in Chromium with the click the
        # engine fires on the root element, past the top edge or the right; in Firefox under Playwright's
        # synthetic mouse a release past the top edge ends with the pointerleave the body fires as the
        # pointer crosses it, and a release past the right edge, level with the banner, ends with NOTHING
        # after the box's own pointerleave: the one open shape (the script's comment names it), pinned here
        # as it stands so a change in what the engine delivers shows up. Its consequence is bounded: the
        # next press anywhere, click or blur ends the flag, and a press elsewhere disarms outright. Where a
        # press does not focus a button (the Gecko switch leg, Safari) the middle press on Restart blurs the
        # label to nothing at its mousedown and, with no primary press recorded, disarms there, as the right
        # press on the message text does everywhere: a secondary click is not a gesture the banner completes
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                p = r["pressEnds"]
                for name in ("intoPane", "outsideRight", "outsideTop", "rightLabel", "middleRestart"):
                    if name == "middleRestart" and engine == "firefox-mousefocus0":
                        self.assertFalse(p[name]["mid"]["armed"], (engine, name, "the middle mousedown blurred the label to nothing: disarmed there"))
                        self.assertFalse(p[name]["recovered"]["armed"], (engine, name))
                        continue
                    self.assertTrue(p[name]["mid"]["armed"], (engine, name, "the gesture itself disarmed", p[name]["mid"]))
                    self.assertIn(p[name]["blurred"], ("rupd-armed", "rupd-confirm"), (engine, name, "focus was still inside the banner"))
                    self.assertFalse(p[name]["recovered"]["armed"], (engine, name, "a press elsewhere disarms whatever the flag holds"))
                    if name == "outsideRight" and engine.startswith("firefox"):
                        self.assertTrue(p[name]["after"]["armed"], (engine, name, "the open shape: no event ends this press under the synthetic mouse; "
                                                                    "if the engine now delivers one, retire the residual from the script's comment and the PR"))
                        continue
                    self.assertFalse(p[name]["after"]["armed"], (engine, name, "the blur after the gesture did not disarm: the press outlived it", p[name]["after"]))
                self.assertFalse(p["rightMessage"]["mid"]["armed"], (engine, "a right press on the message text disarms at its mousedown", p["rightMessage"]["mid"]))
                self.assertEqual(p["rightMessage"]["posts"], p["intoPane"]["posts"], (engine, "nothing posted along the way"))

    def test_the_armed_controls_never_share_a_pixel_with_a_plain_row_control(self):
        # measured at 360, 390, 700, 1000 and 1280 with the standard label, the shortest and the longest:
        # the confirm's rect is disjoint from Update's and Not now's plain rects, so no second activation
        # of one gesture reaches it wherever the first landed, and a click meant for it after a disarm the
        # user did not perform (a new offer pushed, a pane script's focus call) lands on no control;
        # Cancel's rect is disjoint from Update's, so such a click meant for Cancel never arms. On a
        # one-row layout (the label beside the message) the label covers Update's whole plain rect, is at
        # least Update's width, and the confirm begins at least 24 px past both Update's right edge and
        # the label's. The label does not select
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                for variant, widths in (("std", r["widths"]), ("shortest", r["geometry"]["shortest"]), ("longest", r["geometry"]["longest"])):
                    for vw, s in widths.items():
                        where = (engine, variant, vw)
                        self.assertTrue(s["armed"], where)
                        self.assertEqual(s["label"], LABELS[variant], where)
                        go, dm = s["plain"]["go"], s["plain"]["dm"]
                        self.assertTrue(go["width"] and dm["width"], where + ("the plain row was measured",))
                        self.assertTrue(_disjoint(s["cf"], go), where + ("the confirm over Update's plain rect", s["cf"], go))
                        self.assertTrue(_disjoint(s["cf"], dm), where + ("the confirm over Not now's plain rect", s["cf"], dm))
                        self.assertTrue(_disjoint(s["cx"], go), where + ("Cancel over Update's plain rect", s["cx"], go))
                        self.assertGreaterEqual(s["lblRect"]["width"], go["width"] - 0.5, where + ("the label at least Update's width", s["lblRect"], go))
                        self.assertEqual(s["userSelect"], "none", where)
                        self.assertLessEqual(s["scrollWidth"], s["clientWidth"], where + ("the box does not overflow itself", s))
                        self.assertLessEqual(s["docWidth"], s["vw"], where + ("no sideways scroll",))
                        if s["cf"]["top"] < s["lblRect"]["bottom"] and s["cf"]["left"] > s["lblRect"]["left"]:   # the confirm on the label's row
                            self.assertGreaterEqual(s["cf"]["left"], s["lblRect"]["right"] + 24 - 0.5, where + ("24 px past the label", s["cf"], s["lblRect"]))
                        if s["lblRect"]["top"] < s["msg"]["bottom"]:      # the label beside the message: it took Update's place
                            self.assertTrue(_covers(s["lblRect"], go), where + ("the label covers Update's plain rect", s["lblRect"], go))
                            self.assertTrue(s["cf"]["left"] >= go["right"] + 24 - 0.5 or s["cf"]["top"] >= go["bottom"],
                                            where + ("24 px past Update's right edge, or on a row below it", s["cf"], go))
                        else:                                                # the label wrapped: the confirm is below Update's row too
                            self.assertGreaterEqual(s["cf"]["top"], go["bottom"], where + ("the confirm on a row below Update's", s["cf"], go))

    def test_at_phone_widths_the_armed_row_stays_inside_the_viewport_and_a_desktop_keeps_one_row(self):
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                w = r["widths"]
                for vw in ("390", "360"):
                    s = w[vw]
                    self.assertEqual(s["label"], LABEL, (engine, vw))
                    self.assertLessEqual(s["scrollWidth"], s["clientWidth"], (engine, vw, "the box does not overflow itself", s))
                    for name in ("lblRect", "cf", "cx"):
                        self.assertGreaterEqual(s[name]["left"], 0, (engine, vw, name, "starts inside the viewport", s[name]))
                        self.assertLessEqual(s[name]["right"], s["vw"], (engine, vw, name, "ends inside the viewport", s[name]))
                    self.assertLessEqual(s["docWidth"], s["vw"], (engine, vw, "no sideways scroll"))
                    self.assertGreaterEqual(s["lblRect"]["top"], s["msg"]["bottom"], (engine, vw, "the label wrapped under the message", s))
                    self.assertGreaterEqual(s["cf"]["top"], s["lblRect"]["bottom"], (engine, vw, "the buttons dropped under the label", s))
                for vw in ("1000", "1280"):
                    # one row: the label and the buttons sit beside the message (not under it) and level
                    # with each other, and the message keeps one line
                    s = w[vw]
                    self.assertLess(s["cf"]["top"], s["msg"]["bottom"], (engine, vw, "the buttons sit beside the message", s))
                    self.assertEqual(round(s["cf"]["top"]), round(s["cx"]["top"]), (engine, vw, "level with each other", s))
                    self.assertLess(s["msg"]["bottom"] - s["msg"]["top"], 30, (engine, vw, "the message keeps one line", s["msg"]))
                    self.assertLessEqual(s["scrollWidth"], s["clientWidth"], (engine, vw))
                    self.assertLessEqual(s["box"]["right"], s["vw"], (engine, vw))

    def test_the_confirms_red_resolves_through_the_token_at_rest_and_under_the_pointer(self):
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                s = r["widths"]["1280"]
                self.assertEqual(s["cfBg"], "rgb(192, 57, 43)", engine + ": var(--err) resolved to the shell's dark value")
                self.assertEqual(s["cfBgHover"], "rgb(192, 57, 43)", engine + ": the same red under the pointer")


if __name__ == "__main__":
    unittest.main()
