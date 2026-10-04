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
socket is down. The Log is not a tab on the phone: the triangle opens it as a centred modal, and opening marks every entry
it shows seen, and an entry that arrives while the Log is open is seen as it lands, with the same mark (the Log's
markSeen). So with the Log open the triangle is red while a visible pane's socket is down and grey again once it is back,
and an entry logged with the Log open leaves it grey there and after the Log closes; the reopened Log lists that entry.
Before 2026-10-03 such an entry landed unread: it gave the triangle its class has and an unread digit under the open Log
and left both after the Log closed, for a line the reader had seen. On main, where the triangle never turned red, only the
digit showed it; with the colour fix alone it would have been a false red. A muted kind's entries stay unread while it is
muted, at an opening and at an arrival alike, and are seen when an unmute with the Log open lists them (2026-10-04): an
entry is seen when an open Log shows it. Before, that unmute left the triangle with its class has and an unread digit
under the open Log and after the close, for lines just listed. The walk
(tests/log_triangle_browser.mjs) reads the triangle's computed colour at each of the states above, on the tab the shell
opened on and after a tap on another tab, then under the light theme, and reads every other bar button's colour at every
step, so the fix is held to leaving the active tab's accent, the other tabs' grey and the other actions' grey as they
were. The glyph's outline and digit are drawn in currentColor, and each is read as well. The walk mutes a kind, logs two
entries of it, and unmutes it with the Log open, by taps on its toggle; the toggles sit in the Log's panel, so no tap can
unmute with the Log closed. tests/test_error_center.py executes that branch, the desktop's Open log count beside the
triangle, and an arrival with a socket down and the Log open, against the Log script itself.

The red must also read: at least 3:1 (WCAG) against the triangle's ground in both themes. The walk reads that ground at
every step as the computed background of the first box from #merr up whose background is opaque (#mtabs today), and the
ratio is asserted at the steps where the triangle is marked and the Log closed (unread, unreadOtherTab, downUnread,
lightUnread). Not at downOpen: the Log's dimmed overlay (#rerr-back) covers the bar there, so the bar's own background is
not what sits behind the triangle on screen. A ground the walk cannot read (no opaque box, a translucent one, a background
image) fails the leg at those steps; it never skips the ratio. So does an opacity under 1 on any box from #merr up to the
document's root (the round-2 review, 2026-10-04): it dims the triangle, or the triangle and its ground together, so the
two computed colours the ratio is taken from are not what the screen shows.

Red at the base tree in every engine at the first unread step (the computed colour there is the action grey). A mutant
that restores the old precedence (the selector back to `#merr.has`) turns the dark steps red; one without the light rule
turns the light step red; one that leaves an entry that arrives with the Log open unread (the write path before
2026-10-03) turns the openNew step red; one that lists an unmuted kind's entries unread with the Log open (the toggle
before 2026-10-04), or marks only the newest of them, turns the unmutedOpen step red; one that recolours the bar toward
the red (either theme's #mtabs background) turns that theme's contrast assertion red; one that paints the push bell with
the triangle's red (a sibling selector on the triangle's rule) turns the bell's colour assertion red; one that plants an
opacity of 0.3 on the bar (#mtabs), on the triangle itself, on body or on html turns the ground assertion red at the
first contrast step, through the groundError that names the box, not through the ratio.

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
import re
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
# the actions whose colour is the plain action grey in this lab, held at every step: usage, restart, settings, and the push
# bell (#mbell, keyed by its id: it has no data-act), which the push script unhides unconditionally and which wears .on only
# while notifications are on for this device; nothing turns them on in this lab, so it wears the plain grey in both themes.
# The network button wears its own state (.on, .busy) from the remotes poll, so it is held only to not moving with the
# triangle's state
PLAIN_ACTS = ("usage", "restart", "settings", "mbell")
# step: (palette, has, Log open, digit inside the triangle)
STEPS = (("idle", DARK, False, False, "!"),
         ("unread", DARK, True, False, "1"),
         ("unreadOtherTab", DARK, True, False, "1"),
         ("openSeen", DARK, False, True, "!"),
         ("closedSeen", DARK, False, False, "!"),
         ("downUnread", DARK, True, False, "1"),
         ("downOpen", DARK, True, True, "!"),
         ("upOpen", DARK, False, True, "!"),
         ("openNew", DARK, False, True, "!"),
         ("closedNew", DARK, False, False, "!"),
         ("reopenSeen", DARK, False, True, "!"),
         ("mutedOpen", DARK, False, True, "!"),
         ("unmutedOpen", DARK, False, True, "!"),
         ("unmutedClosed", DARK, False, False, "!"),
         ("lightIdle", LIGHT, False, False, "!"),
         ("lightUnread", LIGHT, True, False, "1"))
# the steps where the triangle is marked and the Log closed, so the bar is what sits behind it, and the floor its red keeps
# against that ground there (WCAG 1.4.11's 3:1 for a control's state); downOpen is marked too, under the Log's overlay
CONTRAST_STEPS = ("unread", "unreadOtherTab", "downUnread", "lightUnread")
CONTRAST_FLOOR = 3.0


def _rgb(css):
    """An engine's computed colour, rgb() or rgba() with an alpha of 1, as three channels; anything else is an error."""
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+)(%?))?\s*\)", css or "")
    if not m:
        raise AssertionError("not an rgb() colour: %r" % (css,))
    if m.group(4) is not None and float(m.group(4)) / (100 if m.group(5) else 1) < 1:
        raise AssertionError("a translucent colour cannot be measured alone: %r" % (css,))
    return tuple(float(m.group(i)) for i in (1, 2, 3))


def _contrast(fg, bg):
    """The WCAG 2 contrast ratio of two computed colours."""
    def lum(c):
        ch = [v / 255 for v in _rgb(c)]
        ch = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
    hi, lo = sorted((lum(fg), lum(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


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
        # THE CONTRAST FLOOR (the round-1 review, 2026-10-04): the red reads at 3:1 or better against the triangle's ground,
        # the first box from #merr up with an opaque background, at each closed-Log step where it is marked, in both themes.
        # A ground the walk could not read fails here; the ratio is never skipped. Every step is measured before the one
        # assertion, so a failure names each step under the floor, in either theme
        low = []
        for name in CONTRAST_STEPS:
            s = steps[name]
            self.assertEqual((s["has"], s["logOpen"]), (True, False), "%s %s: a marked triangle under a closed Log: %r"
                             % (engine, name, s))
            self.assertIsNone(s.get("groundError", "the walk read no ground"), "%s %s: the triangle's ground: %r" % (engine, name, s))
            ratio = _contrast(s["color"], s["ground"])
            if ratio < CONTRAST_FLOOR:
                low.append("%s (light theme %s): the red %s at %.2f:1 on %s (%s)" % (name, s["light"], s["color"], ratio,
                                                                                    s["ground"], s["groundOf"]))
        self.assertEqual(low, [], engine + ": the red triangle under the 3:1 floor on its ground")
        # THE ARRIVAL RULE (2026-10-03), second, so a tree that leaves the arrival unread is red for it: an entry logged with
        # the Log open is seen as it lands, so the triangle is grey with the '!' glyph under the open Log and after it closes,
        # and the reopened Log lists the entry. newListed is read at every open step: false before the entry is logged
        for name, listed in (("openSeen", False), ("downOpen", False), ("upOpen", False), ("openNew", True),
                             ("reopenSeen", True)):
            self.assertEqual(steps[name]["newListed"], listed, "%s %s: the open Log lists the entry logged with it open: %r"
                             % (engine, name, steps[name]))
        for name in ("openNew", "closedNew", "reopenSeen"):
            s = steps[name]
            self.assertEqual((s["has"], s["digit"], s["color"]), (False, "!", DARK["idle"]),
                             "%s %s: an entry that arrived with the Log open is seen, so nothing is unread (Log open %s): %r"
                             % (engine, name, s["logOpen"], s))
        # THE UNMUTE RULE (2026-10-04), third, so a tree that lists an unmuted kind's entries unread is red for it: the two
        # entries logged while their kind is muted are not listed; the kind unmuted with the Log open, both are listed and
        # seen, the older as well as the newer, so the triangle is grey with the '!' glyph under the open Log and after it
        # closes. mutedListed and mutedOlderListed are read at every open step
        for key in ("mutedListed", "mutedOlderListed"):
            for name, listed in (("openSeen", False), ("downOpen", False), ("upOpen", False), ("openNew", False),
                                 ("reopenSeen", False), ("mutedOpen", False), ("unmutedOpen", True)):
                self.assertEqual(steps[name][key], listed, "%s %s %s: the open Log lists an entry logged while its kind was "
                                 "muted only once the kind is unmuted: %r" % (engine, name, key, steps[name]))
        for name in ("unmutedOpen", "unmutedClosed"):
            s = steps[name]
            self.assertEqual((s["has"], s["digit"], s["color"]), (False, "!", DARK["idle"]),
                             "%s %s: the entries an unmute listed in the open Log are seen, so nothing is unread (Log open "
                             "%s): %r" % (engine, name, s["logOpen"], s))
        # each one's stored seen flag: absent before it is logged, unread while its kind is muted, seen from the unmute on
        names = [x[0] for x in STEPS]
        for key in ("mutedSeen", "mutedOlderSeen"):
            for i, name in enumerate(names):
                want = None if i < names.index("mutedOpen") else name != "mutedOpen"
                self.assertEqual(steps[name][key], want, "%s %s %s: a muted kind's entry's stored seen flag: %r"
                                 % (engine, name, key, steps[name]))
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
