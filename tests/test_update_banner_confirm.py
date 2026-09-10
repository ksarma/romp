#!/usr/bin/env python3
"""The update banner's Update button takes two clicks (2026-09-10).

One click used to POST /update, which converges main, rebuilds the served bundle and asks the manager
for a restart-all: every session on the box restarts and every turn in flight is cut. A click that only
meant to focus the dashboard window landed on that button. Now the first click ARMS the banner: the
Update button gives its place to a label that states the consequence, in counts (how many sessions the
restart stops and how many of them it interrupts, and whether other kernels restart too), with a red
confirm button and a Cancel beside it; only a click on the confirm posts, carrying {"confirmed": true}.
One gesture never posts, by layout: the second activation of a double-click, a double-tap or a held key
lands where the first did, on the label, which is not a control, whatever click count the engine
reports. Belt and braces on top: the confirm ignores a click whose detail is above 1 (the browser's own
click count) and the buttons ignore a repeated keydown (KeyboardEvent.repeat) for Enter and Space. The
armed state is dropped by exact events, never a timer: Cancel (a click, Enter or Space on it), Escape
through the shell's Escape chain, a press outside the banner in the shell document, a press or a focus in
a pane iframe, focus leaving the banner (a move between the label, the confirm and Cancel keeps it), the
window losing focus, a hidden tab, and every re-render of the banner. The click that focuses the window
therefore never counts: the blur that took focus away disarmed the banner first. An answer without
counts drops the counts the banner held, so the label never shows a previous kernel life's numbers.

EXECUTED, not pinned: node runs the kernel's _UPD_JS (the served banner script, as the browser receives
it) and the shell's Escape chain against fakes for document, window, location and fetch, one process per
scenario, and the scenario reads the banner's state back by name. Then real engines (Playwright's
Chromium and Firefox, skipped loudly where absent) drive the served CSS, markup and script with real
input: a double-click, a held Enter, two taps at the Update button's point, a click on the confirm, a
real click on Cancel, Tab and Enter on Cancel, Escape, a press inside a same-origin iframe, Tab out of
the banner into the iframe, and the phone-width layout. The kernel side (the route's refusal of an
unconfirmed body, the audit row, the counts and the registry read on /update-check) is in
tests/test_kernel_update.py. Synthetic values only."""
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
# carries a window of its own (defaultView) with listeners of its own.
HARNESS = r"""
var LISTENERS = {}, WLISTENERS = {}, FETCHES = [], RELOADS = 0, FOCUS = [], PREVENTED = 0, STOPPED = 0;
function capFlag(cap) { return cap === true || !!(cap && cap.capture); }
function el(id) {
  var classes = {};
  var e = { id: id, hidden: false, disabled: false, textContent: "", onclick: null, children: [], listeners: {},
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
function emit(t, ev) { (LISTENERS[t] || []).forEach(function (l) { l.f(ev || {}); }); }
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
        # decides the wording: with another kernel the label places the counts here and says the others
        # restart too; with one kernel, or while the registry could not be read (null), the plain form
        cases = ((1, 3, 1, "Restart 3 sessions here now, interrupting 1; the other kernels restart too"),
                 (2, 1, 1, "Restart 1 session here now, interrupting 1; the other kernels restart too"),
                 (1, 4, 0, "Restart 4 sessions here now; the other kernels restart too"),
                 (1, 0, 0, "Restart now, nothing to interrupt here; the other kernels restart too"),
                 (0, 3, 1, "Restart 3 sessions now, interrupting 1"),
                 (None, 3, 1, "Restart 3 sessions now, interrupting 1"))
        for others, sessions, mid, want in cases:
            s = run_banner("GO.onclick(); await tick(); await tick(); out(state());",
                           check={"otherKernels": others, "sessions": sessions, "midTurn": mid})
            self.assertEqual(s["label"], want, (others, sessions, mid))
            self.assertEqual(s["posts"], [])
        # the re-read's answer moves the wording too (a kernel added since the page loaded)
        s = run_banner("""
CHECK.otherKernels = 1; GO.onclick(); var atOnce = state(); await tick(); await tick(); out({ atOnce: atOnce, after: state() });""")
        self.assertEqual(s["atOnce"]["label"], "Restart 3 sessions now, interrupting 1")
        self.assertEqual(s["after"]["label"], "Restart 3 sessions here now, interrupting 1; the other kernels restart too")

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
        self.assertIn("<button class=rup-go id=rupd-go>Update</button>", html)
        self.assertIn("<span class=rup-armed id=rupd-armed tabindex=-1 hidden></span>", html)
        self.assertIn("<button class=rup-confirm id=rupd-confirm hidden>Restart</button>", html)
        self.assertIn("<button class=rup-cancel id=rupd-cancel hidden>Cancel</button>", html)
        self.assertLess(html.index("rupd-go"), html.index("rupd-armed"), "the label takes Update's place: next in flow")
        self.assertLess(html.index("rupd-armed"), html.index("rupd-confirm"), "the confirm stands beside the label")
        js = km._UPD_JS
        self.assertIn("body:JSON.stringify({confirmed:true})", js)
        self.assertIn("go.onclick=function(){if(!armed)arm();};", js, "Update only ever arms")
        self.assertIn("cf.onclick=function(e){if(!armed)return;if(e&&e.detail>1)return;", js, "the confirm posts, the click-count guard kept")
        self.assertIn("function noRepeat(e){if(e&&e.repeat&&(e.key==='Enter'||e.key===' '))e.preventDefault();}", js)
        self.assertIn("go.addEventListener('keydown',noRepeat);cf.addEventListener('keydown',noRepeat);", js)

    def test_the_armed_state_ends_on_events_never_a_timer(self):
        js = km._UPD_JS
        for ev in ("cx.onclick=function(){disarm(true);};",
                   "window.__rompUpdDisarm=function(){if(!armed)return false;disarm(true);return true;};",
                   "d.addEventListener('pointerdown',function(){if(armed)disarm();},true);",
                   "var w=d.defaultView;if(w)w.addEventListener('focus',function(){if(armed)disarm();},true);}catch(e){}}",
                   "box.classList.add('rup-arm');wireFrames();",
                   "box.addEventListener('focusout',function(e){if(!armed)return;var t=e&&e.relatedTarget;if(t&&box.contains(t))return;disarm();});",
                   "window.addEventListener('blur',function(){disarm();});",
                   "document.addEventListener('visibilitychange',function(){if(document.hidden)disarm();});",
                   "function show(m){disarm();"):
            self.assertIn(ev, js)
        self.assertNotIn("readyState", js, "a parsing pane document is wired like any other, never skipped")
        # the only timers in the script are the in-flight poll's, none of them touch the armed state
        arm_to_disarm = js[js.index("function disarm("):js.index("function show(")]
        self.assertNotIn("setTimeout", arm_to_disarm)

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
                      "#rupd .rup-msg,#rupd .rup-armed{flex:1 1 100%}#rupd button{flex:1 1 auto;white-space:normal}}", css)
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
try { browser = await pw[cfg.engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const R = { engine: cfg.engine, err: {}, pageErrors: [] };
const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, hasTouch: true });
const page = await ctx.newPage();
page.on("pageerror", (e) => { R.pageErrors.push(String((e && e.message) || e)); });
let posts = 0, dismisses = 0;
await page.route("http://romp.test/**", (route) => {
  const u = new URL(route.request().url());
  const html = (body) => route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body });
  if (u.pathname === "/shell") return html(cfg.page);
  if (u.pathname === "/pane") return html(cfg.pane);
  if (u.pathname === "/update-check") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(cfg.check) });
  if (u.pathname === "/update") { posts++; return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true, state: "running" }) }); }
  if (u.pathname === "/update-dismiss") { dismisses++; return route.fulfill({ status: 200, contentType: "application/json", body: "{}" }); }
  return route.fulfill({ status: 404, body: "" });
});
const load = async () => {
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
  return { armed: box.classList.contains("rup-arm"), shown: box.classList.contains("show"), go: go.textContent, label: lbl.textContent,
           goVisible: go.getClientRects().length > 0, labelHidden: lbl.hidden, confirmHidden: cf.hidden, cancelHidden: cx.hidden,
           notNowHidden: dm.hidden, goDisabled: go.disabled,
           active: a ? (a.id || a.tagName) : "", cfBg: getComputedStyle(cf).backgroundColor,
           box: r(box), goRect: r(go), lblRect: r(lbl), cf: r(cf), cx: r(cx), msg: r(msg), scrollWidth: box.scrollWidth, clientWidth: box.clientWidth,
           vw: window.innerWidth, docWidth: document.documentElement.scrollWidth,
           clicks: window.__clicks.slice(), cxClicks: window.__cxClicks };
});
const center = async (sel) => page.evaluate((s) => { const b = document.querySelector(s).getBoundingClientRect(); return { x: b.left + b.width / 2, y: b.top + b.height / 2 }; }, sel);
const settle = async (want) => { for (let i = 0; i < 100 && posts < want; i++) await new Promise((r) => setTimeout(r, 50)); return posts; };
const step = async (name, fn) => { try { R[name] = await fn(); } catch (e) { R.err[name] = String((e && e.stack) || e); } };

await load();
// 1. widths: armed at a phone width, the label and Cancel stay inside the viewport; a desktop keeps one
// row; at every width the confirm is never where Update was, and a REAL click on Cancel disarms
await step("widths", async () => {
  const out = {};
  for (const w of [390, 360, 700, 1000, 1280]) {
    await page.setViewportSize({ width: w, height: 800 });
    const goPt = await center("#rupd-go");
    await page.click("#rupd-go");
    const s = await st(); s.goPt = goPt;
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
// 2. a press inside the pane iframe disarms (the pane document's own pointerdown; Chromium also blurs the top window)
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
// 6. Tab from the armed state reaches the confirm, then Cancel, without disarming; Enter on Cancel disarms
await load();
await step("tab", async () => {
  const before = posts;
  await page.click("#rupd-go");
  const armed = await st();
  await page.keyboard.press("Tab");
  const onConfirm = await st();
  await page.keyboard.press("Tab");
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
// 8. Tab from Cancel into the pane: focus enters the frame (no focusout in Firefox); the pane window's focus disarms
await step("tabIntoPane", async () => {
  const before = posts;
  await page.click("#rupd-go");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  const onCancel = await st();
  await page.keyboard.press("Tab");
  const after = await st();
  // where focus landed inside the frame: Chromium's first Tab into a frame reaches its first control,
  // Firefox's reaches the frame's document (its body) and the next Tab the control
  const paneActive = await page.frameLocator("#pane").locator("body").evaluate((b) => (b.ownerDocument.activeElement || {}).id || "");
  return { onCancel, after, paneActive, posts: posts - before };
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
            + "</style></head><body>" + km._UPD_HTML
            + "<iframe id=pane src=/pane></iframe><script>" + km._LANDING_ESC_JS + "</script><script>" + km._UPD_JS
            + "</script></body></html>")


PANE = ("<!DOCTYPE html><html><head><meta charset=utf-8></head><body id=pane-body style='margin:0;height:300px'>"
        "pane <button id=pane-btn style='margin-top:120px'>in the pane</button></body></html>")
CHECK = {"cur": "v0.1.0", "tag": "v0.2.0", "mode": "ask", "state": "", "boot": "b1", "drift": "", "driftSha": "",
         "sessions": 32, "midTurn": 3, "otherKernels": 0}       # the long label, the width case that overflowed
LABEL = "Restart 32 sessions now, interrupting 3"


def _contains(rect, pt):
    return rect["left"] <= pt["x"] <= rect["right"] and rect["top"] <= pt["y"] <= rect["bottom"]


class Browser(unittest.TestCase):
    """One driver run per engine over the scratch page; each test reads one facet per engine that ran.
    Skips loudly without playwright or a browser (CI installs none); an engine that fails to launch
    skips its own leg and test_firefox_ran says so."""
    ENGINES = ("chromium", "firefox")
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
        for engine in cls.ENGINES:
            cfg = os.path.join(lab, engine + ".json")
            with open(cfg, "w") as f:
                json.dump({"engine": engine, "page": page, "pane": PANE, "check": CHECK}, f)
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=300,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
            if p.returncode == 3:
                cls.skipped[engine] = "no playwright %s on this box (CI installs none): %s" % (engine, p.stderr.strip()[:200])
                continue
            if p.returncode != 0:
                raise AssertionError("%s driver failed:\n%s%s" % (engine, p.stdout[-3000:], p.stderr[-3000:]))
            line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
            if line is None:
                raise AssertionError("%s driver printed no result:\n%s%s" % (engine, p.stdout[-3000:], p.stderr[-3000:]))
            cls.R[engine] = json.loads(line[len("RESULT:"):])
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

    def test_a_real_click_on_cancel_disarms_and_keeps_the_offer(self):
        # Cancel's mousedown moves focus within the banner (relatedTarget inside), so the disarm waits
        # for the click itself: the handler runs, nothing is posted or dismissed, the offer stays shown
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                for vw, s in r["widths"].items():
                    a = s["afterCancel"]
                    self.assertEqual((a["armed"], a["shown"], a["goVisible"], a["labelHidden"], a["confirmHidden"], a["cancelHidden"], a["notNowHidden"]),
                                     (False, True, True, True, True, True, False), (engine, vw, a))
                    self.assertEqual((a["posts"], a["dismisses"]), (0, 0), (engine, vw))
                    self.assertEqual(a["cxClicks"], 1, (engine, vw, "Cancel's own click handler ran"))
                    self.assertEqual(a["active"], "rupd-go", (engine, vw, "focus back on Update"))

    def test_tab_reaches_the_confirm_and_cancel_and_enter_on_cancel_disarms(self):
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                t = r["tab"]
                self.assertEqual((t["armed"]["armed"], t["armed"]["active"]), (True, "rupd-armed"), engine)
                self.assertEqual((t["onConfirm"]["armed"], t["onConfirm"]["active"]), (True, "rupd-confirm"), engine + ": Tab to the confirm keeps the armed state")
                self.assertEqual((t["onCancel"]["armed"], t["onCancel"]["active"]), (True, "rupd-cancel"), engine + ": Tab to Cancel too")
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

    def test_tab_from_cancel_into_the_pane_disarms(self):
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                t = r["tabIntoPane"]
                self.assertEqual((t["onCancel"]["armed"], t["onCancel"]["active"]), (True, "rupd-cancel"), engine)
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
