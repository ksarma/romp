#!/usr/bin/env python3
"""The Log's filter grid fits the panel on a phone (item 4d, 2026-10-04).

The Log panel opens with a block of "show" toggles, one chip per kind of entry, laid out as an even grid (#rerr-fgrid, the
user 2026-07-28: every chip the same cell width, the fewest rows). Its columns were `repeat(5,1fr)`. A `1fr` track's minimum
is its chips' min-content width, and the chips never wrap (white-space:nowrap), so the five columns could not be narrower
than the widest chip of each side by side, about 341 px in WebKit and Firefox and 362 px in Chromium; the grid, a flex item
with no min-width of its own, kept that width. The panel is min(700px, 94vw) wide, so in WebKit and Firefox the grid ran
past the filter bar's content edge on the right below 414 px of viewport, past the panel below 401 px and off the screen
below 388 to 389 px; in Chromium below 435, 422 and 409 px. At 390 px the last column's three toggles ended 22 px (WebKit,
Firefox) to 43 px (Chromium) past the bar's content edge and 10 to 31 px past the panel's, and in Chromium 19 px past the
screen, so part of each was cut off; at 320 px three to six toggles were cut off by the screen and three could not be tapped
at all. The page itself never scrolled sideways (the panel is in a fixed backdrop), so nothing brought them back.

The columns are now `repeat(auto-fill,minmax(max(var(--rerr-chip-col),20% - 5px),1fr))`: as many equal columns as fit at
96 px or more, and never more than five, since five tracks of a fifth less one gap always fit and a sixth never does.
`--rerr-chip-col` is 96 px, declared once on #rerr-panel: it is also the entry rows' chip column, which is wider than the
widest chip. The desktop's 700 px panel keeps its five equal columns; a phone gets two columns below 368 px, three from
368, four from 475 and five from 583.

The leg drives the served shell in a real engine (Chromium; WebKit and Firefox where the runner declares them) through
tests/log_filter_grid_browser.mjs: the phone (the iPhone 14 descriptor), the Log opened at 390 px by a click on the phone
bar's triangle with one synthetic entry of every kind logged, then the page resized to 320, 360, 368, 375, 390, 414, 430,
475 and 583 px wide (368, 475 and 583 are where a third, fourth and fifth column first fit, so each gives that count's
narrowest cell), first at 844 px high (the iPhone 14's height) and then at 568 px (the shortest phone in use, 320 by 568);
OPEN_W says why it opens at 390. Then the desktop at 821 px (the narrowest width the desktop layout takes, one past
_MOBILE_MQ's 820) and at 1100 px. At each phone size: the grid has the columns PHONE_COLS names for that width (2 at 320
and 360 px, 3 from 368 to 430, 4 at 475, 5 at 583); the page does not scroll sideways; every toggle sits inside the
filter bar's content box across, inside the panel down (above its inner bottom: the bar grows with the grid, so it bounds
nothing vertically) and on the screen both ways, holds its whole label, needs no more than the 96 px floor (the page's
--rerr-chip-col, which no width can narrow a column below, so a label that fits it fits at every width), overlaps no
other toggle and is the element a tap at its centre reaches; every toggle keeps the desktop's font size and height; all
share one width; and the list under the grid keeps at least LIST_FLOOR px (its comment says why). At each desktop width
the grid is five equal columns filling the bar, as before, within the same bounds. A fourth test, in Chromium, runs the
phone pass at 40 widths (one height) and checks that the driver's RESULT line, well over 64 KiB, arrives whole (the driver
writes it in a loop; one write to the pipe used to deliver 64 KiB and drop the rest).

The lab: one kernel from test_ship_reship_served.kernel_env (a private XDG root, `session-hosts` floored off,
ROMP_MANAGER_PORT=1, no catalog or update fetch, a hermetic postal bus), a private dist (lab_dist.copy_dist), no sessions
(the Log needs none). Skips LOUDLY without the extension deps or a Chromium (CI runs the *_served.py files under
ROMP_SERVED_TESTS_REQUIRE=1); the WebKit and Firefox legs are `optional:` skips where that engine is absent or not declared
in ROMP_SERVED_TESTS_ENGINES. The lab kernel uses its own port (tests/lab_ports.py); the driver asserts /healthz on that
port before any request. Synthetic entries only; no real data.
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
# roots), but a later edit that adds a load must not write real state; and that root's per-session hosts off (the Testing
# rule for a test that mints its own state root, 2026-09-11)
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), exist_ok=True)
Path(os.environ["XDG_STATE_HOME"], "romp", "session-hosts").write_text("off\n")

DRIVER = os.path.join(HERE, "log_filter_grid_browser.mjs")
# the phone widths in use, 320 the narrowest the Log must still serve, and 368, 475 and 583: the first width of three, four
# and five columns, so the narrowest cell of each
PHONE_WIDTHS = [320, 360, 368, 375, 390, 414, 430, 475, 583]
PHONE_COLS = {320: 2, 360: 2, 368: 3, 375: 3, 390: 3, 414: 3, 430: 3, 475: 4, 583: 5}   # the columns at each phone width
CHIP_COL = 96   # px: --rerr-chip-col, the columns' floor; no width narrows a column below it, so every label must fit in it
PHONE_HEIGHTS = [844, 568]   # the iPhone 14's height, then the shortest phone in use (320 by 568): every width at each
# px of list kept under the grid at every size: room for three one-line entries (the list's 4 px padding above and below,
# three 27.95 px rows of 11 px text at line-height 1.45 with 6 px of padding above and below, and the 1 px rules between
# them). The tallest grid a phone gets, 2 columns in 8 rows at 320 by 568, leaves the list 112.7 px in all three engines; a
# grid that took more rows would leave less (a 125 px floor gives one column of 15 rows at 320 px, and the list about 8 px)
LIST_FLOOR = 94
OPEN_W = 390   # the Log is opened by its triangle at 390 px, then the page resized: the phone bar is 413 to 418 px wide in this
#                lab, so on a narrower screen its last buttons are past the right edge, the triangle among them below about 355 px
#                (a separate defect: at 320 px a click cannot reach it)
DESKTOP_WIDTHS = [821, 1100]   # 821: the narrowest desktop layout (_MOBILE_MQ's max-width is 820px)
DESKTOP_H = 800
LONG_WIDTHS = list(range(320, 400, 2))   # 40 phone widths: the delivery pin's measures, a RESULT line well over 64 KiB
SLACK = 0.5   # subpixel layout: a box edge may land half a pixel either side


class LogFilterGrid(unittest.TestCase):
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
        cls.lab = tempfile.mkdtemp(prefix="log-fgrid-")
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        claude = os.path.join(cls.lab, "claude")
        os.makedirs(claude, exist_ok=True)
        cls.port, cls.token = lab_ports.reserve(cls.lab), "testtok-logfgrid"
        cls.env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token, ROMP_HOST_NAME="TESTHOST")
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

    def _drive(self, engine, **over):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        cfg = {"engine": engine, "url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token),
               "healthz": "http://127.0.0.1:%d/healthz" % self.port, "bootTimeoutMs": 30000,
               "openWidth": OPEN_W, "phoneWidths": PHONE_WIDTHS, "phoneHeights": PHONE_HEIGHTS,
               "desktopWidths": DESKTOP_WIDTHS, "desktopHeight": DESKTOP_H}
        cfg.update(over)
        cfg_path = os.path.join(self.lab, "cfg-%s.json" % engine)
        Path(cfg_path).write_text(json.dumps(cfg))
        try:
            p = subprocess.run(["node", DRIVER], capture_output=True, text=True, timeout=240,
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
        self._line_bytes = len(line.encode())
        try:
            r = json.loads(line[len("RESULT:"):])
        except ValueError as e:
            self.fail("the RESULT line (%d bytes) does not parse, cut short on its way through the pipe? %s; its tail: %r"
                      % (len(line.encode()), e, line[-200:]))
        self.assertNotIn("died", r, "driver aborted early: %r (kernel log tail: %s)" % (r.get("died"), Path(self.klog).read_text()[-800:]))
        self.assertEqual(r.get("errors"), [], "page errors")
        return r

    def _leg(self, engine):
        r = self._drive(engine)
        kinds = r["kinds"]
        self.assertGreaterEqual(len(kinds), 14, engine + ": the grid shows a toggle for every kind: %r" % (kinds,))
        self.assertEqual(len(set(kinds)), len(kinds), engine + ": one toggle per kind: %r" % (kinds,))
        self.assertEqual([(x["w"], x["h"]) for x in r["phone"]], [(w, h) for h in PHONE_HEIGHTS for w in PHONE_WIDTHS],
                         engine + ": every phone width was read at every height")
        self.assertEqual([x["w"] for x in r["desktop"]], DESKTOP_WIDTHS, engine + ": every desktop width was read")
        # the desktop first: the reference sizes, and the layout the fix keeps (five equal columns filling the bar)
        ref = r["desktop"][0]["m"]["btns"][0]
        for d in r["desktop"]:
            m, where = d["m"], "%s desktop %dpx: " % (engine, d["w"])
            with self.subTest(layout="desktop", width=d["w"]):
                self.assertFalse(m["mobile"], where + "the desktop layout")
                self._fits(m, kinds, where)
                cols = [float(c[:-2]) for c in m["cols"].split()]
                self.assertEqual(len(cols), 5, where + "five columns, as before: %r" % (m["cols"],))
                share = (m["grid"]["w"] - 4 * 5) / 5   # the grid's width less its four 5px gaps, in five
                for c in cols:
                    self.assertAlmostEqual(c, share, delta=SLACK, msg=where + "five EQUAL columns filling the bar: %r" % (m["cols"],))
                self.assertAlmostEqual(m["grid"]["r"], m["barContent"]["r"], delta=SLACK, msg=where + "the grid ends at the bar's content edge")
        # the phone, at every width in use and each height (a subtest each, so a failing run names every size it fails at)
        for ph in r["phone"]:
            m, where = ph["m"], "%s phone %d by %dpx: " % (engine, ph["w"], ph["h"])
            with self.subTest(layout="phone", width=ph["w"], height=ph["h"]):
                self.assertTrue(m["mobile"], where + "the phone layout: %r" % ({k: m[k] for k in ("vw", "mobile")},))
                self.assertTrue(m["logOpen"], where + "the Log is open")
                self.assertEqual((m["vw"], m["vh"]), (ph["w"], ph["h"]), where + "the viewport took the size")
                self.assertEqual(len(m["cols"].split()), PHONE_COLS[ph["w"]],
                                 where + "%d columns at this width: %s (grid %.2f px wide)" % (PHONE_COLS[ph["w"]], m["cols"], m["grid"]["w"]))
                self._fits(m, kinds, where)
                for b in m["btns"]:
                    # the control keeps its size: the desktop's font size and height (the tap area's height; its width is the cell's)
                    self.assertEqual(b["fontSize"], ref["fontSize"], where + "%s keeps its font size: %r" % (b["text"], b))
                    self.assertAlmostEqual(b["h"], ref["h"], delta=SLACK, msg=where + "%s keeps its height: %r" % (b["text"], b))
                widths = [b["w"] for b in m["btns"]]
                self.assertLessEqual(max(widths) - min(widths), 1, where + "an even grid: every toggle the same cell width: %r" % (widths,))

    def _fits(self, m, kinds, where):
        """Every toggle inside the bar's content box across, inside the panel down (its border stripped), and on the screen
        both ways; whole, unshared, reachable; no sideways scroll; and the list keeps LIST_FLOOR px under the grid. Down, the
        bound is the panel's inner bottom, not the bar's: the bar grows with the grid, so a grid too tall for the panel would
        carry the bar's box past the panel with it and still sit inside the bar."""
        btns = m["btns"]
        self.assertEqual([b["kind"] for b in btns], kinds, where + "the toggles are the kinds, in order")
        self.assertLessEqual(m["docSW"], m["docCW"], where + "the page does not scroll sideways: %r" % ({k: m[k] for k in ("docSW", "docCW")},))
        self.assertEqual(m["scrollX"], 0, where + "the page cannot be scrolled sideways")
        self.assertLessEqual(m["grid"]["r"], m["barContent"]["r"] + SLACK,
                             where + "the grid ends inside the filter bar: grid %r, bar content %r, cols %s" % (m["grid"], m["barContent"], m["cols"]))
        for b in btns:
            what = where + "%s: %r" % (b["text"], b)
            self.assertEqual((b["display"], b["visibility"]), ("block", "visible"), what)
            self.assertGreaterEqual(b["l"], m["barContent"]["l"] - SLACK, what + " starts inside the bar")
            self.assertLessEqual(b["r"], m["barContent"]["r"] + SLACK, what + " ends inside the bar (bar content right %.2f)" % m["barContent"]["r"])
            self.assertGreaterEqual(b["l"], -SLACK, what + " starts on screen")
            self.assertLessEqual(b["r"], m["vw"] + SLACK, what + " ends on screen (viewport %d)" % m["vw"])
            self.assertGreaterEqual(b["t"], m["panelInner"]["t"] - SLACK, what + " starts inside the panel (inner top %.2f)" % m["panelInner"]["t"])
            self.assertLessEqual(b["b"], m["panelInner"]["b"] + SLACK, what + " ends inside the panel (inner bottom %.2f)" % m["panelInner"]["b"])
            self.assertGreaterEqual(b["t"], -SLACK, what + " starts on screen")
            self.assertLessEqual(b["b"], m["vh"] + SLACK, what + " ends on screen (viewport height %d)" % m["vh"])
            self.assertLessEqual(b["need"], b["w"] + SLACK, what + " holds its whole label")
            self.assertLessEqual(b["need"], CHIP_COL, what + " needs no more than the %d px floor, the narrowest a column gets" % CHIP_COL)
            self.assertTrue(b["hit"], what + " is what a tap at its centre reaches")
        for i, a in enumerate(btns):
            for b in btns[i + 1:]:
                apart = a["r"] <= b["l"] + SLACK or b["r"] <= a["l"] + SLACK or a["b"] <= b["t"] + SLACK or b["b"] <= a["t"] + SLACK
                self.assertTrue(apart, where + "%s and %s overlap: %r %r" % (a["text"], b["text"], a, b))
        self.assertGreaterEqual(m["list"]["h"], LIST_FLOOR, where + "the list keeps %d px under the grid: list %r, panel %r, grid %r"
                                % (LIST_FLOOR, m["list"], m["panel"], m["grid"]))
        # last, so a run against a tree without the property reports the geometry first: the label bound above is CHIP_COL,
        # and this says the page's floor is that same width
        self.assertEqual(m["chipCol"], "%dpx" % CHIP_COL, where + "the page's --rerr-chip-col is the floor the labels are checked against")

    def test_chromium_the_filter_grid_fits_the_phone_and_keeps_the_desktop(self):
        self._leg("chromium")

    # WebKit is Safari's engine (the phone's); an `optional:` skip where the browser is absent (CI installs Chromium alone)
    def test_webkit_the_filter_grid_fits_the_phone_and_keeps_the_desktop(self):
        self._leg("webkit")

    def test_firefox_the_filter_grid_fits_the_phone_and_keeps_the_desktop(self):
        self._leg("firefox")

    def test_chromium_the_driver_delivers_a_result_line_over_64_kib_whole(self):
        """The driver's RESULT line arrives whole however long it is (2026-10-05). The driver runs
        under playwright, which leaves its stdout non-blocking, and one writeSync to this pipe wrote 64 KiB and dropped the
        rest, so a longer line (more widths, more kinds, a page error per toggle) failed every leg with a parse error that
        named neither the width nor the property. Here the phone pass alone runs at LONG_WIDTHS, enough measures for a line
        well over 64 KiB, and every width must come back. Chromium only: the write is node's, the same in every engine."""
        r, size = self._drive("chromium", phoneWidths=LONG_WIDTHS, phoneHeights=PHONE_HEIGHTS[:1], desktopWidths=[]), self._line_bytes
        self.assertGreater(size, 65536, "the premise: this line is longer than one pipe write delivered (%d bytes)" % size)
        self.assertEqual([x["w"] for x in r["phone"]], LONG_WIDTHS, "every width's measure arrived")


if __name__ == "__main__":
    unittest.main()
