#!/usr/bin/env python3
"""The phone bar's Log triangle turns red when the Log holds something unread (iOS item 4a, 2026-10-03).

The Log's opener on the phone is the warning triangle in the bottom bar's action cluster (#merr, data-act=errs). The Log's
script (_LANDING_ERRS_JS paint) puts the class `has` on it while an unmuted entry is unread or a visible pane's socket is
down, and the shell's `#merr.has{color:#ff6b6b}` was meant to paint it red. It never did: the mobile block's action-button
grey, `#mtabs button.mact{color:#7d848b}`, has one id, one class and one type and outranks the bare `#merr.has` (one id, one
class) whatever their order; in the light theme `body.theme-light #mtabs button{color:#5D574E}` (one id, one class, two
types) outranks it too. So the one cue the control carries never showed. The fix gives the rule two ids, `#mtabs
#merr.has`, which outranks both, and gives the light theme its own red, the light palette's error red #B02A1C (the API
health failure line's), since the dark red is about 2:1 on the light bar, fainter than the idle grey.

What the triangle shows, from the design (the paint comment): red while anything unread is in the Log or a visible pane's
socket is down. The Log is not a tab on the phone: the triangle opens it as a centred modal, and opening marks every shown
entry seen, so with the Log open the triangle is red only while a live problem stands, and grey again once the socket is
back. The walk (tests/log_triangle_browser.mjs) reads the triangle's computed colour at each of those states, on the tab the
shell opened on and after a tap on another tab, then under the light theme, and reads every other bar button's colour at
every step, so the fix is held to leaving the active tab's accent, the other tabs' grey and the other actions' grey as they
were. The glyph's outline and digit are drawn in currentColor, and each is read as well.

Red at the base tree in every engine at the first unread step (the computed colour there is the action grey). A mutant
that restores the old precedence (the selector back to `#merr.has`) turns the dark steps red; one without the light rule
turns the light step red.

The lab: one kernel from test_ship_reship_served.kernel_env (a private XDG root, `session-hosts` floored off,
ROMP_MANAGER_PORT=1, no catalog or update fetch, a hermetic postal bus), its port and its wait from tests/lab_ports.py, a
private dist (lab_dist.copy_dist), no sessions. Skips LOUDLY without the extension deps or a Chromium (CI runs the
*_served.py files under ROMP_SERVED_TESTS_REQUIRE=1); the WebKit and Firefox legs are `optional:` skips where the engine is
absent or not declared in ROMP_SERVED_TESTS_ENGINES. Synthetic Log entries only; no real data.
"""
import json
import lab_dist
import lab_ports
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab                      # noqa: E402  (kernel_env: every lab kernel's environment)

# Hermetic state BEFORE anything: this module loads no romp code in-process (the kernel is a subprocess under kernel_env's
# roots), but a later edit that adds a load must not write real state, and that root's per-session hosts are off (the
# Testing rule for a test that mints its own state root, 2026-09-11)
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), exist_ok=True)
Path(os.environ["XDG_STATE_HOME"], "romp", "session-hosts").write_text("off\n")

DRIVER = os.path.join(HERE, "log_triangle_browser.mjs")

# The colours as the engines report them, written out here rather than read from kernel.py, so a product edit cannot move
# what the test expects. Dark: the triangle's red, the action grey, the active tab's blue, the tabs' grey. Light: the light
# palette's error red, its bar grey (tabs and actions alike), its clay for the active tab.
DARK = {"red": "rgb(255, 107, 107)", "idle": "rgb(125, 132, 139)", "tabOn": "rgb(77, 164, 255)",
        "tab": "rgb(154, 160, 166)", "act": "rgb(125, 132, 139)"}
LIGHT = {"red": "rgb(176, 42, 28)", "idle": "rgb(93, 87, 78)", "tabOn": "rgb(194, 65, 12)",
         "tab": "rgb(93, 87, 78)", "act": "rgb(93, 87, 78)"}
# the actions whose colour is the plain action grey in this lab; the network button wears its own state (.on, .busy) from
# the remotes poll, so it is held only to not moving with the triangle's state
PLAIN_ACTS = ("usage", "restart", "settings")
# step: (palette, has, Log open, digit inside the triangle)
STEPS = (("idle", DARK, False, False, "!"),
         ("unread", DARK, True, False, "1"),
         ("unreadOtherTab", DARK, True, False, "1"),
         ("openSeen", DARK, False, True, "!"),
         ("closedSeen", DARK, False, False, "!"),
         ("downUnread", DARK, True, False, "1"),
         ("downOpen", DARK, True, True, "!"),
         ("upOpen", DARK, False, True, "!"),
         ("lightIdle", LIGHT, False, False, "!"),
         ("lightUnread", LIGHT, True, False, "1"))


class LogTriangle(unittest.TestCase):
    """One lab kernel for every leg (setUpClass); each leg is one driver run in one engine."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.kernel, cls.lab = None, None
        try:
            cls._boot()
        except BaseException:
            cls.tearDownClass()
            raise

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served leg needs them")
        cls.lab = tempfile.mkdtemp(prefix="log-tri-")
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        cls.port, cls.token = lab_ports.reserve(cls.lab), "testtok-logtri"
        cls.env = _lab.kernel_env(cls.lab, os.path.join(cls.lab, "claude"), dist, cls.port, cls.token)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"),
                                      stderr=subprocess.STDOUT, env=cls.env)
        why = lab_ports.wait_owned(cls.kernel, cls.env)
        if why:
            raise unittest.SkipTest("hermetic kernel never served /healthz here: " + why)

    @classmethod
    def tearDownClass(cls):
        if cls.kernel:
            try:
                os.kill(cls.kernel.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            cls.kernel.wait()
        if cls.lab:
            lab_ports.release(cls.lab)
            shutil.rmtree(cls.lab, ignore_errors=True)

    def _drive(self, engine):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        cfg = {"engine": engine, "url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token),
               "healthz": "http://127.0.0.1:%d/healthz" % self.port, "bootTimeoutMs": 30000, "settleMs": 500}
        cfg_path = os.path.join(self.lab, "cfg-%s.json" % engine)
        Path(cfg_path).write_text(json.dumps(cfg))
        try:
            p = subprocess.run(["node", DRIVER], capture_output=True, text=True, timeout=180,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg_path))
        except subprocess.TimeoutExpired as e:
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            self.fail("driver timed out; partial output:\n%s" % so[-3000:])
        if p.returncode == 3:
            if engine == "chromium":
                self.skipTest("no playwright chromium on this box: the served leg needs one (CI installs it)")
            self.skipTest("optional: no playwright %s on this machine: %s" % (engine, p.stderr.strip()[-300:]))
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        r = json.loads(line[len("RESULT:"):])
        self.assertNotIn("died", r, "driver aborted early: %r (steps read: %s; kernel log tail: %s)"
                         % (r.get("died"), sorted(r.get("steps", {})), Path(self.klog).read_text()[-800:]))
        self.assertEqual(r.get("errors"), [], "page errors")
        return r

    def _leg(self, engine):
        r = self._drive(engine)
        steps = r["steps"]
        self.assertEqual(sorted(steps), sorted(s[0] for s in STEPS), engine + ": every step was read")
        # THE DEFECT, first, so a tree without the fix is red for it: an unread entry paints the triangle red, on the tab the
        # shell opened on and on another tab, in the dark theme and in the light one
        for name in ("unread", "unreadOtherTab", "downUnread", "downOpen", "lightUnread"):
            s, pal = steps[name], dict((x[0], x[1]) for x in STEPS)[name]
            self.assertTrue(s["has"], "%s %s: the Log's script marked the triangle: %r" % (engine, name, s))
            self.assertEqual(s["color"], pal["red"], "%s %s: the marked triangle is red (tab %s, Log open %s); the rules that "
                             "match #merr and set a colour, in document order: %s"
                             % (engine, name, s["tab"], s["logOpen"], json.dumps(s["rules"])))
        prev_tab = None
        for name, pal, has, log_open, digit in STEPS:
            s = steps[name]
            where = "%s %s: " % (engine, name)
            self.assertNotIn("missing", s, where + "the triangle is in the bar")
            self.assertEqual(s["barDisplay"], "flex", where + "the phone layout shows the bar")
            self.assertEqual(s["light"], pal is LIGHT, where + "the theme: %r" % (s,))
            self.assertEqual((s["has"], s["logOpen"], s["digit"]), (has, log_open, digit), where + "the Log's state: %r" % (s,))
            self.assertEqual(s["color"], pal["red"] if has else pal["idle"],
                             where + "the triangle's colour; rules matching #merr: %s" % json.dumps(s["rules"]))
            # the outline and the digit are drawn in currentColor, so each follows the triangle's colour
            self.assertEqual((s["stroke"], s["textFill"]), (s["color"], s["color"]), where + "the glyph's paint: %r" % (s,))
            # every other button keeps its own colour: one pane tab active (the one shown) in the accent, the rest in the
            # tabs' grey, the plain actions in the action grey
            tabs = [b for b in s["others"] if b["key"].startswith("pane:")]
            on = [b["key"] for b in tabs if b["on"]]
            self.assertEqual(on, ["pane:" + s["tab"]], where + "exactly the shown tab is active: %r" % (tabs,))
            for b in tabs:
                self.assertEqual(b["color"], pal["tabOn"] if b["on"] else pal["tab"], where + "pane tab %r" % (b,))
            acts = dict((b["key"], b["color"]) for b in s["others"] if not b["key"].startswith("pane:"))
            for k in PLAIN_ACTS:
                self.assertEqual(acts.get(k), pal["act"], where + "action %s keeps the action colour: %r" % (k, acts))
            self.assertIn("net", acts, where + "the network action is in the bar: %r" % (acts,))
            if name == "unreadOtherTab":
                self.assertNotEqual(s["tab"], prev_tab, where + "the walk tapped another tab")
            prev_tab = s["tab"]
        # the network action's colour does not move with the triangle's state, within each theme
        for pal in (DARK, LIGHT):
            nets = set(steps[n]["others"][[b["key"] for b in steps[n]["others"]].index("net")]["color"]
                       for n, p, _h, _o, _d in STEPS if p is pal)
            self.assertEqual(len(nets), 1, engine + ": the network action's colour stays put while the triangle changes: %r" % (nets,))

    def test_chromium_phone_log_triangle_is_red_while_the_log_holds_something(self):
        self._leg("chromium")

    # WebKit is Safari's engine and Firefox the third; each an `optional:` skip where absent (CI installs Chromium alone)
    def test_webkit_phone_log_triangle_is_red_while_the_log_holds_something(self):
        self._leg("webkit")

    def test_firefox_phone_log_triangle_is_red_while_the_log_holds_something(self):
        self._leg("firefox")


if __name__ == "__main__":
    unittest.main()
