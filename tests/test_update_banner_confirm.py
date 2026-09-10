#!/usr/bin/env python3
"""The update banner's Update button takes two clicks (2026-09-10).

One click used to POST /update, which converges main, rebuilds the served bundle and asks the manager
for a restart-all: every session on the box restarts and every turn in flight is cut. A click that only
meant to focus the dashboard window landed on that button. Now the first click ARMS the button (it
restates itself as the consequence, in counts: how many sessions the restart stops and how many of them
it interrupts, with a Cancel beside it) and only a click on the armed button posts, carrying
{"confirmed": true}. One gesture never posts: the armed click ignores the second and third clicks of a
double- or triple-click (e.detail, the browser's own click count). The armed state is dropped by exact
events, never a timer: Cancel, a press outside the banner in the shell document, focus leaving the
armed button (into a pane iframe, another control, or nothing), the window losing focus, a hidden tab,
and every re-render of the banner. The click that focuses the window therefore never counts: the blur
that took focus away disarmed the button first.

EXECUTED, not pinned: node runs the kernel's _UPD_JS (the served banner script, as the browser receives
it) against fakes for document, window, location and fetch, one process per scenario, and the scenario
reads the banner's state back by name. Then real engines (Playwright's Chromium and Firefox, skipped
loudly where absent) drive the served CSS, markup and script with real input: a double-click, a press
inside a same-origin iframe, and the phone-width layout. The kernel side (the route's refusal of an
unconfirmed body, the audit row, the counts on /update-check) is in tests/test_kernel_update.py.
Synthetic values only."""
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
# gesture events by name, and every fetch is recorded with its method and body.
HARNESS = r"""
var LISTENERS = {}, WLISTENERS = {}, FETCHES = [], RELOADS = 0;
function capFlag(cap) { return cap === true || !!(cap && cap.capture); }
function el(id) {
  var classes = {};
  var e = { id: id, hidden: false, disabled: false, textContent: "", onclick: null, children: [], listeners: {},
    classList: { add: function (c) { classes[c] = 1; }, remove: function (c) { delete classes[c]; },
                 contains: function (c) { return !!classes[c]; } },
    addEventListener: function (t, f, cap) { (e.listeners[t] = e.listeners[t] || []).push({ f: f, cap: capFlag(cap) }); },
    contains: function (n) {
      if (n === e) return true;
      for (var i = 0; i < e.children.length; i++) if (e.children[i].contains(n)) return true;
      return false;
    } };
  return e;
}
var BOX = el("rupd"), MSG = el("rup-msg"), GO = el("rupd-go"), CX = el("rupd-cancel"), DM = el("rupd-dismiss");
var ELSEWHERE = el("elsewhere");                     // a node outside the banner
BOX.children = [MSG, GO, CX, DM];
GO.textContent = "Update"; CX.hidden = true;         // the served markup's initial state
BOX.querySelector = function (sel) { return sel === ".rup-msg" ? MSG : null; };
// the pane iframes: same-origin documents of their own, whose events never reach the shell document
function paneDoc() {
  var d = { readyState: "complete", listeners: {} };
  d.addEventListener = function (t, f, cap) { (d.listeners[t] = d.listeners[t] || []).push({ f: f, cap: capFlag(cap) }); };
  return d;
}
function frame(id) {
  var f = { id: id, listeners: {}, contentDocument: paneDoc() };
  f.addEventListener = function (t, fn, cap) { (f.listeners[t] = f.listeners[t] || []).push({ f: fn, cap: capFlag(cap) }); };
  return f;
}
var PANE = frame("f-chat"), FRAMES = [PANE];
var document = {
  hidden: false,
  addEventListener: function (t, f, cap) { (LISTENERS[t] = LISTENERS[t] || []).push({ f: f, cap: capFlag(cap) }); },
  getElementById: function (id) { return { "rupd": BOX, "rupd-go": GO, "rupd-cancel": CX, "rupd-dismiss": DM }[id] || null; },
  getElementsByTagName: function (t) { return t === "iframe" ? FRAMES : []; }
};
var window = { addEventListener: function (t, f, cap) { (WLISTENERS[t] = WLISTENERS[t] || []).push({ f: f, cap: capFlag(cap) }); } };
var location = { reload: function () { RELOADS++; } };
var CHECK = { cur: "v0.1.0", tag: "v0.2.0", mode: "ask", state: "", boot: "b1", drift: "", driftSha: "", sessions: 3, midTurn: 1 };
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
function tick() { return new Promise(function (r) { setTimeout(r, 0); }); }
function posts() { return FETCHES.filter(function (f) { return f.url === "/update"; }); }
function state() {
  return { shown: BOX.classList.contains("show"), msg: MSG.textContent, go: GO.textContent,
           armed: GO.classList.contains("rup-arm"), goHidden: GO.hidden, goDisabled: GO.disabled,
           cancelHidden: CX.hidden, notNowHidden: DM.hidden, posts: posts(),
           checks: FETCHES.filter(function (f) { return f.url === "/update-check"; }).length, reloads: RELOADS,
           pointerdownCapture: (LISTENERS.pointerdown || []).map(function (l) { return l.cap; }),
           goFocusout: (GO.listeners.focusout || []).length,
           paneWired: FRAMES.map(function (f) { return (f.contentDocument.listeners.pointerdown || []).map(function (l) { return l.cap; }); }),
           paneLoad: FRAMES.map(function (f) { return (f.listeners.load || []).length; }) };
}
// the wait after a confirmed POST polls /update-check on a 3 s timer; the scenario ends the process
// once its result is out, so no poll ever fires
function out(o) { process.stdout.write("RESULT:" + JSON.stringify(o) + "\n"); setTimeout(function () { process.exit(0); }, 0); }
"""


def run_banner(scenario, check=None):
    """Run the served banner script, let its load-time /update-check land (two ticks) so the offer
    shows, then the scenario. `check` overrides fields of the /update-check answer before the load."""
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed")
    pre = "".join("CHECK[%s] = %s;\n" % (json.dumps(k), json.dumps(v)) for k, v in (check or {}).items())
    d = tempfile.mkdtemp(prefix="upd-banner-")
    path = os.path.join(d, "banner.js")
    with open(path, "w") as f:
        f.write(HARNESS + pre + km._UPD_JS + "\n(async function(){\nawait tick(); await tick();\n" + scenario + "\n})();\n")
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
        self.assertEqual((b["shown"], b["go"], b["cancelHidden"], b["notNowHidden"], b["armed"]),
                         (True, "Update", True, False, False), "the offer as served: Update and Not now")
        a = s["atOnce"]
        self.assertEqual(a["posts"], [], "the first click posts nothing")
        self.assertTrue(a["armed"])
        self.assertEqual(a["go"], "Restart 3 sessions now, interrupting 1",
                         "the button restates itself as the consequence, from the counts the banner holds")
        self.assertEqual((a["cancelHidden"], a["notNowHidden"], a["goDisabled"]), (False, True, False),
                         "Cancel stands beside the armed button; Not now steps aside")
        self.assertEqual(a["checks"], 2, "the arm re-reads /update-check for the counts as they stand now")
        self.assertTrue(a["shown"])
        self.assertEqual(s["settled"]["posts"], [], "still nothing posted once the re-read landed")
        self.assertTrue(s["settled"]["armed"])

    def test_the_arm_re_reads_the_counts_and_the_label_follows(self):
        s = run_banner("""
CHECK.sessions = 5; CHECK.midTurn = 2;                 // the box changed since the page loaded
GO.onclick(); var atOnce = state(); await tick(); await tick();
out({ atOnce: atOnce, after: state() });""")
        self.assertEqual(s["atOnce"]["go"], "Restart 3 sessions now, interrupting 1", "the held answer, at once")
        self.assertEqual(s["after"]["go"], "Restart 5 sessions now, interrupting 2", "the re-read's answer")
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
            self.assertEqual(s["go"], want, (sessions, mid))
            self.assertEqual(s["posts"], [])

    def test_unknown_counts_arm_with_the_label_without_counts_and_the_re_read_fills_them_in(self):
        # /update-check answers null while the kernel's SDK backend is still being built: the banner
        # must still arm (never a plain-looking Update with armed set, which the next click would post
        # through) and must not claim 0/0. Both offer paths: the load-time offer and the kernel push
        for name, check, push in (
                ("load", {"sessions": None, "midTurn": None}, ""),
                ("push", {"mode": "", "tag": "", "sessions": None, "midTurn": None},
                 "window.__rompUpdateOffer('v0.1.0','v0.2.0','','b1','');")):
            s = run_banner(push + """
CHECK.sessions = 2; CHECK.midTurn = 0;               // the kernel knows by the time of the click
GO.onclick(); var atOnce = state(); await tick(); await tick(); var filled = state();
GO.onclick(); await tick(); out({ atOnce: atOnce, filled: filled, after: state() });""", check=check)
            a = s["atOnce"]
            self.assertEqual((a["go"], a["armed"], a["posts"], a["shown"]),
                             ("Restart every session now", True, [], True), name)
            self.assertEqual(s["filled"]["go"], "Restart 2 sessions now", name + ": the arm's re-read fills the counts in")
            self.assertEqual(len(s["after"]["posts"]), 1, name + ": the second click on the armed button posts once")

    def test_the_second_click_posts_once_with_the_confirmation(self):
        s = run_banner("""
GO.onclick(); await tick(); await tick();
GO.onclick(); var atOnce = state(); await tick(); await tick();
out({ atOnce: atOnce, after: state() });""")
        a = s["atOnce"]
        self.assertEqual(len(a["posts"]), 1, "the armed click posts")
        p = a["posts"][0]
        self.assertEqual((p["method"], p["body"], p["type"]), ("POST", {"confirmed": True}, "application/json"))
        self.assertTrue(a["goDisabled"], "acknowledged at once: the button disables under the click")
        self.assertFalse(a["armed"], "the armed state ends with the click that used it")
        self.assertTrue(a["msg"].startswith("Updating romp"))
        self.assertEqual(len(s["after"]["posts"]), 1, "once")
        self.assertEqual(s["after"]["reloads"], 0)

    def test_a_double_click_arms_and_posts_nothing_and_a_later_click_posts_once(self):
        # the browser's own click count (e.detail): the second click of a double-click carries 2, and
        # the armed click ignores it, so one gesture never completes the confirm; no timer of ours.
        # The button stays armed, so a single click after the OS multi-click interval confirms
        s = run_banner("""
GO.onclick({ detail: 1 }); GO.onclick({ detail: 2 }); var dbl = state(); await tick(); await tick();
GO.onclick({ detail: 1 }); var later = state(); await tick();
out({ dbl: dbl, later: later });""")
        self.assertEqual((s["dbl"]["posts"], s["dbl"]["armed"]), ([], True), "the double-click arms and stops")
        self.assertEqual(len(s["later"]["posts"]), 1, "a separate single click on the armed button posts")

    def test_a_triple_click_posts_nothing_and_a_keyboard_activation_posts_once(self):
        # Enter or Space on the focused button is a click with detail 0: it confirms
        s = run_banner("""
GO.onclick({ detail: 1 }); GO.onclick({ detail: 2 }); GO.onclick({ detail: 3 }); var triple = state(); await tick();
GO.onclick({ detail: 0 }); out({ triple: triple, keyboard: state() });""")
        self.assertEqual((s["triple"]["posts"], s["triple"]["armed"]), ([], True))
        self.assertEqual(len(s["keyboard"]["posts"]), 1)

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
        self.assertEqual((r["armed"], r["go"], r["cancelHidden"], r["notNowHidden"]), (False, "Update", True, False))
        self.assertIn("v0.3.0", r["msg"])
        self.assertEqual((s["rearmed"]["armed"], s["rearmed"]["posts"]), (True, []), "arms again, posts nothing")
        self.assertEqual((s["running"]["armed"], s["running"]["goHidden"], s["running"]["posts"]), (False, True, []))

    def test_the_boot_retire_disarms_too(self):
        s = run_banner("""
GO.onclick(); await tick(); var armed1 = state();
window.__rompUpdBoot('b2'); out({ armed1: armed1, after: state() });""")
        self.assertTrue(s["armed1"]["armed"])
        self.assertEqual((s["after"]["armed"], s["after"]["shown"], s["after"]["go"], s["after"]["posts"]),
                         (False, False, "Update", []))

    def test_cancel_a_press_elsewhere_a_blur_or_a_hidden_tab_disarms_and_a_press_inside_does_not(self):
        s = run_banner("""
GO.onclick(); await tick(); CX.onclick(); var cancelled = state();
GO.onclick(); await tick(); emit('pointerdown', { target: GO }); var inside = state();
emit('pointerdown', { target: ELSEWHERE }); var outside = state();
GO.onclick(); await tick(); wemit('blur'); var blurred = state();
GO.onclick(); await tick(); document.hidden = true; emit('visibilitychange'); var hidden = state();
document.hidden = false;
out({ cancelled: cancelled, inside: inside, outside: outside, blurred: blurred, hidden: hidden });""")
        c = s["cancelled"]
        self.assertEqual((c["armed"], c["go"], c["cancelHidden"], c["notNowHidden"], c["shown"]),
                         (False, "Update", True, False, True), "Cancel: back to the offer, still showing")
        self.assertTrue(s["inside"]["armed"], "a press on the banner itself keeps the armed state")
        self.assertFalse(s["outside"]["armed"], "a press anywhere else drops it")
        self.assertEqual(s["outside"]["pointerdownCapture"], [True],
                         "the document listener is capture-phase: a shell control that stops propagation cannot hide the press")
        self.assertFalse(s["blurred"]["armed"], "focus leaving the window drops it")
        self.assertFalse(s["hidden"]["armed"], "a hidden tab drops it")
        for k in ("cancelled", "inside", "outside", "blurred", "hidden"):
            self.assertEqual(s[k]["posts"], [], k)

    def test_focus_leaving_the_armed_button_disarms(self):
        # the third disarm: a press inside a pane iframe reaches neither the shell document's pointerdown
        # nor, in Firefox, the shell window's blur; it does move focus off the button, and focusout on the
        # button fires in every engine that focuses a button on click. A plain button never sees it
        s = run_banner("""
var plain = state(); eemit(GO, 'focusout'); var plainAfter = state();
GO.onclick(); await tick(); eemit(GO, 'focusout'); var left = state();
GO.onclick(); var rearmed = state(); await tick();
out({ plain: plain, plainAfter: plainAfter, left: left, rearmed: rearmed });""")
        self.assertEqual(s["plain"]["goFocusout"], 1, "one focusout listener on the button itself")
        self.assertEqual((s["plainAfter"]["armed"], s["plainAfter"]["go"]), (False, "Update"), "a no-op while plain")
        self.assertEqual((s["left"]["armed"], s["left"]["go"], s["left"]["cancelHidden"], s["left"]["posts"]),
                         (False, "Update", True, []), "focus left the armed button: plain again")
        self.assertEqual((s["rearmed"]["armed"], s["rearmed"]["posts"]), (True, []), "the next click arms, never posts")

    def test_a_press_inside_a_pane_disarms_through_the_panes_own_document(self):
        # a press in a pane never reaches the shell document, and in Firefox fires neither the shell
        # window's blur nor the button's focusout (the Browser leg below measures that), so the banner
        # wires each pane document's own pointerdown, capture phase, once: at load, on the frame's
        # (re)load (a pane that reloads while armed gets a fresh document), and at every arm (a frame
        # added since the page loaded)
        s = run_banner("""
var wired = state(); GO.onclick(); await tick(); eemit(PANE.contentDocument, 'pointerdown'); var pressed = state();
PANE.contentDocument = paneDoc(); eemit(PANE, 'load');                       // the pane reloaded
GO.onclick(); await tick(); var rearmed = state(); eemit(PANE.contentDocument, 'pointerdown'); var pressed2 = state();
var LATE = frame('f-late'); FRAMES.push(LATE); var added = state();          // a frame added since the page loaded
GO.onclick(); await tick(); var armed3 = state(); eemit(LATE.contentDocument, 'pointerdown'); var pressed3 = state();
out({ wired: wired, pressed: pressed, rearmed: rearmed, pressed2: pressed2, added: added, armed3: armed3, pressed3: pressed3 });""")
        self.assertEqual((s["wired"]["paneWired"], s["wired"]["paneLoad"]), ([[True]], [1]),
                         "wired at load, capture phase, with one load handler on the frame")
        self.assertEqual((s["pressed"]["armed"], s["pressed"]["go"]), (False, "Update"), "a press in the pane disarms")
        self.assertEqual(s["rearmed"]["paneWired"], [[True]], "the reloaded pane's new document is wired once (load and arm do not stack)")
        self.assertEqual(s["rearmed"]["paneLoad"], [1], "and the frame keeps its one load handler")
        self.assertFalse(s["pressed2"]["armed"], "a press in the reloaded pane disarms")
        self.assertEqual(s["added"]["paneWired"], [[True], []], "a frame added later is not wired yet")
        self.assertEqual((s["armed3"]["paneWired"], s["armed3"]["paneLoad"]), ([[True], [True]], [1, 1]), "the arm wires it")
        self.assertFalse(s["pressed3"]["armed"])
        for k in ("pressed", "pressed2", "pressed3"):
            self.assertEqual(s[k]["posts"], [], k)

    def test_the_click_that_focuses_the_window_never_posts(self):
        # the incident's shape: the button was left armed, focus went to another window (blur), and
        # the click that brought focus back landed on the button. The blur disarmed it, so that click
        # finds a plain Update and arms it; nothing is posted
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
GO.onclick(); await tick(); await tick(); GO.onclick(); await tick(); await tick(); await tick();
out(state());""")
        self.assertEqual(len(s["posts"]), 1)
        self.assertTrue(s["msg"].startswith("Could not start the update: the update starts only from a confirmed click"))
        self.assertEqual((s["armed"], s["go"], s["goDisabled"], s["notNowHidden"]), (False, "Update", False, False))


class Wiring(unittest.TestCase):
    """Source pins on the parts node does not execute: the markup, the stylesheet and the kernel route."""

    def test_the_markup_carries_the_cancel_button_hidden_and_the_post_carries_the_confirmation(self):
        self.assertIn("<button class=rup-cancel id=rupd-cancel hidden>Cancel</button>", km._UPD_HTML)
        self.assertIn("body:JSON.stringify({confirmed:true})", km._UPD_JS)
        self.assertIn("go.onclick=function(e){if(!armed){arm();return;}if(e&&e.detail>1)return;", km._UPD_JS)

    def test_the_armed_state_ends_on_events_never_a_timer(self):
        js = km._UPD_JS
        for ev in ("cx.onclick=function(){disarm();};",
                   "d.addEventListener('pointerdown',function(){if(armed)disarm();},true);}catch(e){}}",
                   "cx.hidden=false;dm.hidden=true;wireFrames();",
                   "go.addEventListener('focusout',function(){disarm();});",
                   "window.addEventListener('blur',function(){disarm();});",
                   "document.addEventListener('visibilitychange',function(){if(document.hidden)disarm();});",
                   "function show(m){disarm();"):
            self.assertIn(ev, js)
        # the only timers in the script are the in-flight poll's, none of them touch the armed state
        arm_to_disarm = js[js.index("function disarm()"):js.index("function show(")]
        self.assertNotIn("setTimeout", arm_to_disarm)

    def test_the_armed_red_is_the_error_token_the_shell_defines_for_both_themes(self):
        # ui/CLAUDE.md: a hex only as a var() fallback. The shell loads no sheet, so it defines --err
        # inline, in both themes, and the armed rule reads it
        css = km._UPD_CSS
        self.assertIn("#rupd .rup-go.rup-arm{background:var(--err,#c0392b);", css)
        self.assertNotIn("rup-arm{background:#", css, "never the bare hex")
        html = km._landing()
        html = html if isinstance(html, str) else html.decode("utf-8")
        self.assertIn(":root{--err:#c0392b}", html)
        self.assertIn("body.theme-light{--err:#B02A1C}", html)

    def test_the_box_sizes_to_its_content_and_wraps_inside_the_viewport(self):
        # a fixed box with left:50% shrink-to-fit against the half viewport: a long armed label wrapped
        # the message on a desktop and pushed Cancel past a phone's edge. max-content sizing, wrap, and
        # the sibling banner's phone rule (the Browser leg below measures all three widths)
        css = km._UPD_CSS
        self.assertIn("z-index:99999;display:none;flex-wrap:wrap;width:max-content;align-items:center;gap:12px;"
                      "max-width:92vw;box-sizing:border-box;", css)
        self.assertIn("@media (max-width:640px){#rupd{width:92vw;gap:10px 12px}"
                      "#rupd .rup-msg{flex:1 1 100%}#rupd button{flex:1 1 auto;white-space:normal}}", css)
        self.assertIn("#rupd .rup-go.rup-arm:hover:not(:disabled){background:var(--err,#c0392b);", css,
                      "the armed hover restates the red: the green hover rule has the same specificity")

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
# The served CSS, markup and script on a scratch page beside a same-origin iframe (a pane), driven with
# real input in Playwright's Chromium and Firefox. The page's --err token is the shell's own line, lifted
# from _landing(). /update-check and /update are answered by the driver, which counts the posts.
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
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on("pageerror", (e) => { R.pageErrors.push(String((e && e.message) || e)); });
let posts = 0;
await page.route("http://romp.test/**", (route) => {
  const u = new URL(route.request().url());
  const html = (body) => route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body });
  if (u.pathname === "/shell") return html(cfg.page);
  if (u.pathname === "/pane") return html(cfg.pane);
  if (u.pathname === "/update-check") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(cfg.check) });
  if (u.pathname === "/update") { posts++; return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true, state: "running" }) }); }
  return route.fulfill({ status: 404, body: "" });
});
const load = async () => {
  await page.goto("http://romp.test/shell");
  await page.waitForFunction(() => document.getElementById("rupd").classList.contains("show"), null, { timeout: 15000 });
  await page.waitForFunction(() => document.getElementById("pane").contentDocument && document.getElementById("pane").contentDocument.getElementById("pane-body"), null, { timeout: 15000 });
};
const st = () => page.evaluate(() => {
  const box = document.getElementById("rupd"), go = document.getElementById("rupd-go"), cx = document.getElementById("rupd-cancel"), msg = box.querySelector(".rup-msg");
  const r = (n) => { const b = n.getBoundingClientRect(); return { left: b.left, right: b.right, top: b.top, bottom: b.bottom, width: b.width }; };
  const a = document.activeElement;
  return { armed: go.classList.contains("rup-arm"), go: go.textContent, cancelHidden: cx.hidden, goDisabled: go.disabled,
           active: a ? (a.id || a.tagName) : "", goBg: getComputedStyle(go).backgroundColor,
           box: r(box), goRect: r(go), cx: r(cx), msg: r(msg), scrollWidth: box.scrollWidth, clientWidth: box.clientWidth,
           vw: window.innerWidth, docWidth: document.documentElement.scrollWidth };
});
const settle = async (want) => { for (let i = 0; i < 100 && posts < want; i++) await new Promise((r) => setTimeout(r, 50)); return posts; };
const disarmViaCancel = () => page.evaluate(() => document.getElementById("rupd-cancel").onclick());
const step = async (name, fn) => { try { R[name] = await fn(); } catch (e) { R.err[name] = String((e && e.stack) || e); } };

await load();
// 1. widths: armed at a phone width, the label and Cancel stay inside the viewport; a desktop keeps one row
await step("widths", async () => {
  const out = {};
  for (const w of [390, 360, 1000, 1280]) {
    await page.setViewportSize({ width: w, height: 800 });
    await page.click("#rupd-go");
    const hover = (await st()).goBg;                  // the pointer still rests on the button it armed
    await page.mouse.move(5, 790);
    const s = await st(); s.goBgHover = hover; out[w] = s;
    await disarmViaCancel();
  }
  await page.setViewportSize({ width: 1280, height: 800 });
  return out;
});
// 2. a press inside the pane iframe disarms (focusout on the button; Chromium also blurs the top window)
await step("pane", async () => {
  await page.click("#rupd-go");
  const armed = await st();
  await page.frameLocator("#pane").locator("#pane-body").click();
  const after = await st();
  return { armed, after, posts };
});
// 3. a double-click arms and posts nothing; an activation afterwards (Enter on the focused button) posts once
await load();
await step("dbl", async () => {
  const before = posts;
  await page.dblclick("#rupd-go");
  const afterDbl = await st();
  const postsDbl = await settle(before + 1);          // give a stray post every chance to land: none may
  await page.focus("#rupd-go");
  await page.keyboard.press("Enter");
  const postsEnter = await settle(before + 1);
  return { afterDbl, postsDbl: postsDbl - before, postsEnter: postsEnter - before, after: await st() };
});
await browser.close();
process.stdout.write("RESULT:" + JSON.stringify(R) + "\n");
process.exit(0);
"""


def _scratch_page():
    """The shell's --err line, the banner's CSS, markup and script, and a pane iframe below the banner."""
    html = km._landing()
    html = html if isinstance(html, str) else html.decode("utf-8")
    tok = re.search(r":root\{--err:#[0-9a-fA-F]{6}\}", html)     # Wiring pins that it exists; without it
    #                                                                   the armed rule's var() fallback paints
    return ("<!DOCTYPE html><html><head><meta charset=utf-8><style>" + (tok.group(0) if tok else "") + km._UPD_CSS
            + "iframe#pane{position:fixed;top:220px;left:20px;width:300px;height:300px;border:1px solid #888}"
            + "</style></head><body>" + km._UPD_HTML
            + "<iframe id=pane src=/pane></iframe><script>" + km._UPD_JS + "</script></body></html>")


PANE = "<!DOCTYPE html><html><head><meta charset=utf-8></head><body id=pane-body style='margin:0;height:300px'>pane</body></html>"
CHECK = {"cur": "v0.1.0", "tag": "v0.2.0", "mode": "ask", "state": "", "boot": "b1", "drift": "", "driftSha": "",
         "sessions": 32, "midTurn": 3}       # the long label, the width case that overflowed


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
        # the pane case is Firefox's: a press in a same-origin frame fires no top-window blur there
        if "firefox" in self.skipped:
            self.skipTest(self.skipped["firefox"])
        self.assertIn("firefox", self.R)

    def test_a_press_inside_a_pane_iframe_disarms(self):
        # the pane's own document hears the press (wireFrames): in Firefox focus moves into the frame and
        # neither the shell window's blur nor the button's focusout fires, so this is the disarm that counts
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                p = r["pane"]
                self.assertEqual((p["armed"]["armed"], p["armed"]["active"]), (True, "rupd-go"),
                                 engine + ": the first click armed and focused the button")
                self.assertFalse(p["after"]["armed"], engine + ": a press in the pane disarmed it (state: %r)" % p["after"])
                self.assertEqual((p["after"]["go"], p["after"]["cancelHidden"]), ("Update", True), engine)
                self.assertEqual(p["posts"], 0, engine)

    def test_a_double_click_posts_nothing_and_an_activation_after_it_posts_once(self):
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                d = r["dbl"]
                self.assertEqual((d["postsDbl"], d["afterDbl"]["armed"]), (0, True),
                                 engine + ": the double-click armed and posted nothing (state: %r)" % d["afterDbl"])
                self.assertEqual(d["postsEnter"], 1, engine + ": Enter on the armed button posted once")
                self.assertTrue(d["after"]["goDisabled"], engine + ": and the button disabled under it")

    def test_at_phone_widths_the_armed_label_and_cancel_stay_inside_the_viewport_and_a_desktop_keeps_one_row(self):
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                w = r["widths"]
                for vw in ("390", "360"):
                    s = w[vw]
                    self.assertTrue(s["armed"], (engine, vw))
                    self.assertEqual(s["go"], "Restart 32 sessions now, interrupting 3", (engine, vw))
                    self.assertLessEqual(s["scrollWidth"], s["clientWidth"], (engine, vw, "the box does not overflow itself", s))
                    self.assertGreaterEqual(s["cx"]["left"], 0, (engine, vw, "Cancel starts inside the viewport", s["cx"]))
                    self.assertLessEqual(s["cx"]["right"], s["vw"], (engine, vw, "Cancel ends inside the viewport", s["cx"]))
                    self.assertLessEqual(s["goRect"]["right"], s["vw"], (engine, vw, "so does the armed button", s["goRect"]))
                    self.assertLessEqual(s["docWidth"], s["vw"], (engine, vw, "no sideways scroll"))
                    self.assertGreaterEqual(s["goRect"]["top"], s["msg"]["bottom"], (engine, vw, "the buttons wrapped under the message", s))
                for vw in ("1000", "1280"):
                    # one row: the buttons sit beside the message (not under it) and level with each other,
                    # and the message keeps one line (a box capped at half the viewport wrapped it to two)
                    s = w[vw]
                    self.assertLess(s["goRect"]["top"], s["msg"]["bottom"], (engine, vw, "the buttons sit beside the message", s))
                    self.assertEqual(round(s["goRect"]["top"]), round(s["cx"]["top"]), (engine, vw, "level with each other", s))
                    self.assertLess(s["msg"]["bottom"] - s["msg"]["top"], 30, (engine, vw, "the message keeps one line", s["msg"]))
                    self.assertLessEqual(s["scrollWidth"], s["clientWidth"], (engine, vw))
                    self.assertLessEqual(s["box"]["right"], s["vw"], (engine, vw))

    def test_the_armed_red_resolves_through_the_token_at_rest_and_under_the_pointer(self):
        # the shell's dark --err; and the same red while the pointer still rests on the button it just
        # armed (the plain button's green hover rule has the same specificity and would otherwise win)
        for engine, r in self.R.items():
            with self.subTest(engine=engine):
                s = r["widths"]["1280"]
                self.assertEqual(s["goBg"], "rgb(192, 57, 43)", engine + ": var(--err) resolved to the shell's dark value")
                self.assertEqual(s["goBgHover"], "rgb(192, 57, 43)", engine + ": red under the pointer too, not the plain hover green")


if __name__ == "__main__":
    unittest.main()
