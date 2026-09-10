#!/usr/bin/env python3
"""The update banner's Update button takes two clicks (2026-09-10).

One click used to POST /update, which converges main, rebuilds the served bundle and asks the manager
for a restart-all: every session on the box restarts and every turn in flight is cut. A click that only
meant to focus the dashboard window landed on that button. Now the first click ARMS the button (it
restates itself as the consequence, in counts: how many sessions the restart stops and how many are
mid-turn, with a Cancel beside it) and only a click on the armed button posts, carrying
{"confirmed": true}. The armed state is dropped by exact events, never a timer: Cancel, a press outside
the banner, the window losing focus, a hidden tab, and every re-render of the banner. The click that
focuses the window therefore never counts: the blur that took focus away disarmed the button first.

EXECUTED, not pinned: node runs the kernel's _UPD_JS (the served banner script, as the browser receives
it) against fakes for document, window, location and fetch, one process per scenario, and the scenario
reads the banner's state back by name. The kernel side (the route's refusal of an unconfirmed body, the
audit row, the counts on /update-check) is in tests/test_kernel_update.py. Synthetic values only."""
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
km = load_source("romp_kernel_upd_confirm", os.path.join(BIN, "romp-kernel"))

# The page the banner script thinks it runs in. `var` at module scope shadows node's globals; the
# script's own document/window listeners land in LISTENERS/WLISTENERS so a scenario can emit the
# gesture events by name, and every fetch is recorded with its method and body.
HARNESS = r"""
var LISTENERS = {}, WLISTENERS = {}, FETCHES = [], RELOADS = 0;
function el(id) {
  var classes = {};
  var e = { id: id, hidden: false, disabled: false, textContent: "", onclick: null, children: [],
    classList: { add: function (c) { classes[c] = 1; }, remove: function (c) { delete classes[c]; },
                 contains: function (c) { return !!classes[c]; } },
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
var document = {
  hidden: false,
  addEventListener: function (t, f) { (LISTENERS[t] = LISTENERS[t] || []).push(f); },
  getElementById: function (id) { return { "rupd": BOX, "rupd-go": GO, "rupd-cancel": CX, "rupd-dismiss": DM }[id] || null; }
};
var window = { addEventListener: function (t, f) { (WLISTENERS[t] = WLISTENERS[t] || []).push(f); } };
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
function emit(t, ev) { (LISTENERS[t] || []).forEach(function (f) { f(ev || {}); }); }
function wemit(t, ev) { (WLISTENERS[t] || []).forEach(function (f) { f(ev || {}); }); }
function tick() { return new Promise(function (r) { setTimeout(r, 0); }); }
function posts() { return FETCHES.filter(function (f) { return f.url === "/update"; }); }
function state() {
  return { shown: BOX.classList.contains("show"), msg: MSG.textContent, go: GO.textContent,
           armed: GO.classList.contains("rup-arm"), goHidden: GO.hidden, goDisabled: GO.disabled,
           cancelHidden: CX.hidden, notNowHidden: DM.hidden, posts: posts(),
           checks: FETCHES.filter(function (f) { return f.url === "/update-check"; }).length, reloads: RELOADS };
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
        self.assertEqual(a["go"], "Restart 3 sessions now, 1 mid-turn",
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
        self.assertEqual(s["atOnce"]["go"], "Restart 3 sessions now, 1 mid-turn", "the held answer, at once")
        self.assertEqual(s["after"]["go"], "Restart 5 sessions now, 2 mid-turn", "the re-read's answer")
        self.assertEqual(s["after"]["posts"], [])

    def test_the_label_reads_naturally_for_one_session_none_live_and_none_mid_turn(self):
        cases = ((1, 1, "Restart 1 session now, 1 mid-turn"),
                 (4, 0, "Restart 4 sessions now"),
                 (0, 0, "Restart now, no sessions live"))
        for sessions, mid, want in cases:
            s = run_banner("GO.onclick(); await tick(); await tick(); out(state());",
                           check={"sessions": sessions, "midTurn": mid})
            self.assertEqual(s["go"], want, (sessions, mid))
            self.assertEqual(s["posts"], [])

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
        self.assertFalse(s["blurred"]["armed"], "focus leaving the window drops it")
        self.assertFalse(s["hidden"]["armed"], "a hidden tab drops it")
        for k in ("cancelled", "inside", "outside", "blurred", "hidden"):
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
    """Source pins on the parts node does not execute: the markup and the kernel route."""

    def test_the_markup_carries_the_cancel_button_hidden_and_the_post_carries_the_confirmation(self):
        self.assertIn("<button class=rup-cancel id=rupd-cancel hidden>Cancel</button>", km._UPD_HTML)
        self.assertIn("body:JSON.stringify({confirmed:true})", km._UPD_JS)
        self.assertIn("go.onclick=function(){if(!armed){arm();return;}", km._UPD_JS)

    def test_the_armed_state_ends_on_events_never_a_timer(self):
        js = km._UPD_JS
        for ev in ("cx.onclick=function(){disarm();};",
                   "document.addEventListener('pointerdown',function(e){if(armed&&!(e&&e.target&&box.contains(e.target)))disarm();},true);",
                   "window.addEventListener('blur',function(){disarm();});",
                   "document.addEventListener('visibilitychange',function(){if(document.hidden)disarm();});",
                   "function show(m){disarm();"):
            self.assertIn(ev, js)
        # the only timers in the script are the in-flight poll's, none of them touch the armed state
        arm_to_disarm = js[js.index("function disarm()"):js.index("function show(")]
        self.assertNotIn("setTimeout", arm_to_disarm)

    def test_the_route_refuses_a_body_without_the_confirmation_before_reading_any_check(self):
        src = km_src()
        route = src[src.index('if u.path == "/update":'):src.index('if u.path == "/notify-all":')]
        self.assertIn('if b.get("confirmed") is not True:', route)
        self.assertLess(route.index('if b.get("confirmed") is not True:'), route.index("tag = _UPDATE_AVAIL[0]"),
                        "refused before the kernel's own checks are read")
        self.assertEqual(route.count('via="update-confirmed"'), 2, "both doors the click can take audit the confirmation")


def km_src():
    with open(os.path.join(BIN, "romp-kernel"), encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    unittest.main()
