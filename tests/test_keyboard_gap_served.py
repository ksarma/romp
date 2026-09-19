#!/usr/bin/env python3
"""The phone shell leaves no empty band between the chat composer and the keyboard (D1, 2026-09-19).

The report (the user 2026-09-18, again 2026-09-19 with a screenshot; iPhone, the installed app, iOS 18): with the keyboard
up the composer sat about 80 CSS px above the keyboard's accessory bar and the band between them was bare page background.
The shell's keyboard model is --app-h = visualViewport.height and --mtabs-h collapsing to 0 while kbOpen() reads the
keyboard as up; nothing read visualViewport.offsetTop. iOS reveals a focused input by PANNING the visual viewport down
the layout viewport (offsetTop > 0) while the layout viewport keeps its height, so a body sized to vv.height at layout y 0
covered 0..vv.height while the visible band ran offsetTop..offsetTop+vv.height: the bottom offsetTop pixels of the screen
showed the html background with the composer at its top edge. fit() now publishes the pan as --app-top and the mobile body
rule fixes the body at it (kernel.py _LANDING_MOBILE_JS and the mobile media block); the second cause, a bar reservation
surviving a keyboard that shrinks the layout viewport too, is pinned by tests/test_kernel_mobile.MobileFitExecutes.

This leg drives the served shell in a real engine (Chromium, and WebKit where the runner declares it) with the iPhone 14
descriptor: an init script replaces the top document's window.visualViewport with a settable fake before the shell script
parses (tests/keyboard_gap_browser.mjs), the driver moves it the way an iOS keyboard slide does (height 844 to 508,
offsetTop 0 to 83, resize then scroll), and the assertion is geometric: the composer's bottom in the shell's coordinate
space keeps the same distance from the visible band's bottom edge as at rest (no band), --mtabs-h is 0px, the body's box
IS the visible band, and #mtabs's box still ends at the true bottom of the layout viewport (a fixed panel's containing
block is the viewport, not the fixed body). On the base tree the composer stops 83 px short of the band.

The lab: one kernel from test_ship_reship_served.kernel_env (a private XDG root, `session-hosts` floored off,
ROMP_MANAGER_PORT=1, no catalog or update fetch, a hermetic postal bus), a private dist (lab_dist.copy_dist), the three
synthetic notes-api sessions test_return_from_background_served seeds (placeholder uuids, host TESTHOST). Skips LOUDLY
without the extension deps or a Chromium (CI runs the *_served.py files under ROMP_SERVED_TESTS_REQUIRE=1); the WebKit
leg is an `optional:` skip where that engine is absent or not declared in ROMP_SERVED_TESTS_ENGINES. The lab kernel uses
its own port; the driver asserts /healthz on that port before any request. Synthetic sessions only; no real data.
"""
import json
import lab_dist
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab                      # noqa: E402  (kernel_env: every lab kernel's environment)
import test_return_from_background_served as _ret          # noqa: E402  (_seed: the notes-api demo's three synthetic sessions)

# Hermetic state BEFORE anything: this module loads no romp code in-process (the kernel is a subprocess under
# kernel_env's roots), but the floor costs two lines and a later edit that adds a load must not write real state.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

DRIVER = os.path.join(HERE, "keyboard_gap_browser.mjs")
HOST = "TESTHOST"
LAYOUT_H = 844      # the iPhone 14 descriptor's layout viewport under the shell's viewport meta
KB_H, KB_PAN = 508, 83   # the visual viewport with the keyboard up, and iOS's pan of it


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def _px(v):
    """'83px' -> 83.0; an empty or malformed value is a failure, not a zero."""
    v = (v or "").strip()
    assert v.endswith("px"), "not a px value: %r" % (v,)
    return float(v[:-2])


class KeyboardGap(unittest.TestCase):
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
        cls.lab = tempfile.mkdtemp(prefix="kb-gap-")
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        cls.state, claude = _ret._seed(cls.lab)
        cls.port, cls.token = _free_port(), "testtok-kbgap"
        seams = {"ROMP_HOST_NAME": HOST}
        cls.env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token, **seams)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"),
                                      stderr=subprocess.STDOUT, env=cls.env)
        for _ in range(120):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/healthz" % cls.port, timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise unittest.SkipTest("hermetic kernel never served /healthz here")

    @classmethod
    def tearDownClass(cls):
        if cls.kernel:
            try:
                os.kill(cls.kernel.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            cls.kernel.wait()
        if cls.lab:
            shutil.rmtree(cls.lab, ignore_errors=True)

    def _drive(self, engine):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        cfg = {"engine": engine, "url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token),
               "healthz": "http://127.0.0.1:%d/healthz" % self.port, "bootTimeoutMs": 30000, "settleMs": 500,
               "shots": os.path.join(self.lab, "kb-gap-" + engine) if os.environ.get("KB_GAP_SHOTS") else ""}
        cfg_path = os.path.join(self.lab, "cfg-%s.json" % engine)
        Path(cfg_path).write_text(json.dumps(cfg))
        try:
            p = subprocess.run(["node", DRIVER], capture_output=True, text=True, timeout=120,
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
        self.assertNotIn("died", r, "driver aborted early: %r (kernel log tail: %s)" % (r.get("died"), Path(self.klog).read_text()[-800:]))
        self.assertTrue(r.get("ready"), "the chat composer never laid out under the shell: %r" % (r,))
        self.assertEqual(r.get("errors"), [], "page errors")
        return r

    def _leg(self, engine):
        r = self._drive(engine)
        where = engine + ": "
        rest, up, down, nopan, settled = r["rest"], r["kbUp"], r["kbDown"], r["kbNoPan"], r["settled"]
        # the emulation held: the shell read the fake visual viewport, in a layout viewport of the descriptor's height
        for name, g in (("rest", rest), ("kbUp", up), ("pickerUp", r["pickerUp"]), ("kbDown", down), ("kbNoPan", nopan),
                        ("pinchPanned", r["pinchPanned"]), ("kbDownZoomed", r["kbDownZoomed"])):
            self.assertTrue(g["vv"]["fake"], where + name + ": the shell's visualViewport is the fake")
            self.assertIsNone(g["labVVError"], where + name)
            self.assertEqual(g["innerHeight"], LAYOUT_H, where + name + ": the layout viewport is the descriptor's")
            self.assertEqual(g["scrollY"], 0, where + name + ": the layout never scrolls")
            self.assertIsNotNone(g["composerBottom"], where + name + ": the composer has a box")
        # THE GAP, first: at rest the composer sits a fixed distance above the visible band's bottom edge (the bar's strip,
        # measured from --mtabs-h); with the keyboard up and iOS's pan the band's bottom is offsetTop + height, and the
        # composer must keep that distance. The base tree stopped 83 px short of it (an empty band the pan's height).
        bar_h = _px(rest["mtabsH"])
        self.assertGreater(bar_h, 0, where + "the bar's height is measured at rest: %r" % (rest,))
        rest_gap = (LAYOUT_H - bar_h) - rest["composerBottom"]   # the composer's distance from the band's bottom, above the bar
        self.assertGreaterEqual(rest_gap, -0.5, where + "the composer is not under the bar at rest: %r" % (rest,))
        self.assertLessEqual(rest_gap, 8, where + "the composer is flush with the band at rest (the footer's own slack only): %r" % (rest,))
        band_bottom = KB_PAN + KB_H
        self.assertAlmostEqual(band_bottom - up["composerBottom"], rest_gap, delta=1,
                               msg=where + "the composer keeps its distance from the visible band's bottom under the pan (no empty band): %r" % (up,))
        # the shell's fixed panels stay glued to the TRUE bottom: the bar's box ends at the layout viewport's bottom, behind the keyboard
        self.assertAlmostEqual(up["bar"]["bottom"], LAYOUT_H, delta=0.5, msg=where + "#mtabs stays at the layout viewport's bottom under the pan: %r" % (up,))
        self.assertEqual(up["bar"]["display"], "flex", where + "the bar is not hidden by the shell, only by the keyboard")
        # at rest: the bar shows, reserved at its measured height, the body in the fixed mobile rule at the top of the band
        self.assertEqual(rest["bar"]["display"], "flex", where + "the phone layout shows the bar")
        self.assertAlmostEqual(rest["bar"]["height"], bar_h, delta=1, msg=where + "the reservation is the bar's height")
        self.assertEqual(rest["body"]["position"], "fixed", where + "the mobile body rule applies")
        self.assertEqual(_px(rest["appTop"]), 0, where + "no pan at rest")
        self.assertAlmostEqual(rest["body"]["top"], 0, delta=0.5, msg=where + "body at rest")
        self.assertAlmostEqual(rest["body"]["bottom"], LAYOUT_H, delta=0.5, msg=where + "body at rest")
        # the keyboard up with the pan, in the shell's own terms: the pan published, the body IS the visible band, the strip collapsed
        self.assertEqual(_px(up["appH"]), KB_H, where + "--app-h follows the visual viewport: %r" % (up,))
        self.assertEqual(_px(up["appTop"]), KB_PAN, where + "--app-top is the pan: %r" % (up,))
        self.assertEqual(_px(up["mtabsH"]), 0, where + "the bar's strip collapses with the keyboard up: %r" % (up,))
        self.assertAlmostEqual(up["body"]["top"], KB_PAN, delta=0.5, msg=where + "the body starts at the pan: %r" % (up,))
        self.assertAlmostEqual(up["body"]["bottom"], band_bottom, delta=0.5, msg=where + "the body ends at the band's bottom: %r" % (up,))
        # the new-session picker lifted under the same keyboard and pan (round 2, 2026-09-19): the lift is the other fixed box
        # sized by --app-h, and at top 0 it sat a pan above the body, so the band survived under the picker. Its box IS the
        # body's, which is the visible band. The base tree put it at 0..508 against a body at 83..591.
        pk, rel = r["pickerUp"], r["pickerDown"]
        self.assertIsNotNone(pk["lifted"], where + "the shell lifted the chat frame on the picker's ask: %r" % (pk,))
        self.assertEqual((pk["lifted"]["id"], pk["lifted"]["position"]), ("f-chat", "fixed"), where + "%r" % (pk["lifted"],))
        self.assertEqual(_px(pk["appTop"]), KB_PAN, where + "the pan stands with the picker up: %r" % (pk,))
        self.assertAlmostEqual(pk["body"]["top"], KB_PAN, delta=0.5, msg=where + "the body stays at the pan under the lift: %r" % (pk,))
        self.assertAlmostEqual(pk["lifted"]["top"], pk["body"]["top"], delta=0.5, msg=where + "the lift's top is the body's: %r" % (pk["lifted"],))
        self.assertAlmostEqual(pk["lifted"]["bottom"], pk["body"]["bottom"], delta=0.5, msg=where + "the lift's bottom is the body's: %r" % (pk["lifted"],))
        self.assertAlmostEqual(pk["lifted"]["bottom"], band_bottom, delta=0.5, msg=where + "the lift ends at the band's bottom: %r" % (pk["lifted"],))
        # the emulation held under the lift: on this layout the lifted pane is display:contents with an empty box, so render.ts
        # placeLifted (the transcript backing at the pane's rect) takes its gone branch and nothing measures the lift's origin
        self.assertEqual((pk["lifted"]["pane"]["display"], pk["lifted"]["pane"]["width"], pk["lifted"]["pane"]["height"]), ("contents", 0, 0),
                         where + "the lifted pane has no box on the phone layout: %r" % (pk["lifted"]["pane"],))
        self.assertIsNone(rel["lifted"], where + "the lift is released on the picker's close: %r" % (rel,))
        self.assertAlmostEqual(rel["body"]["top"], KB_PAN, delta=0.5, msg=where + "%r" % (rel,))
        # the keyboard down: the pan is gone, the strip is back, the composer is where it was
        self.assertEqual(_px(down["appTop"]), 0, where + "no pan with the keyboard down: %r" % (down,))
        self.assertEqual(_px(down["appH"]), LAYOUT_H, where + "%r" % (down,))
        self.assertEqual(_px(down["mtabsH"]), bar_h, where + "the strip returns with the keyboard down: %r" % (down,))
        self.assertAlmostEqual(down["composerBottom"], rest["composerBottom"], delta=0.5, msg=where + "the composer returns to its resting place: %r" % (down,))
        self.assertAlmostEqual(down["body"]["top"], 0, delta=0.5, msg=where + "%r" % (down,))
        # a keyboard with no pan: the body stays at the top and the composer sits flush above the band's bottom (the model before D1)
        self.assertEqual(_px(nopan["appTop"]), 0, where + "%r" % (nopan,))
        self.assertEqual(_px(nopan["mtabsH"]), 0, where + "%r" % (nopan,))
        self.assertAlmostEqual(KB_H - nopan["composerBottom"], rest_gap, delta=1, msg=where + "flush above the band with no pan: %r" % (nopan,))
        self.assertAlmostEqual(settled["composerBottom"], rest["composerBottom"], delta=0.5, msg=where + "%r" % (settled,))
        # a pinch after the pan, and the keyboard dismissed while zoomed (round 2, 2026-09-19): zoomed with the keyboard up the
        # pan holds and the body is still the band; with the keyboard gone and the zoom standing, --app-h is the full height
        # again, and a held pan would place the body at 83..927 with the composer row below the viewport. The held pan is
        # clamped to the layout viewport less that height, so the body stays inside it and the composer stays reachable.
        pz, dz, zb = r["pinchPanned"], r["kbDownZoomed"], r["zoomBack"]
        self.assertEqual(pz["vv"]["scale"], 2, where + "the shell read the zoom: %r" % (pz["vv"],))
        self.assertEqual((_px(pz["appTop"]), _px(pz["appH"])), (KB_PAN, KB_H), where + "zoomed with the keyboard up, the pan holds: %r" % (pz,))
        self.assertAlmostEqual(pz["body"]["bottom"], band_bottom, delta=0.5, msg=where + "%r" % (pz,))
        self.assertEqual(_px(dz["appH"]), LAYOUT_H, where + "%r" % (dz,))
        self.assertLessEqual(dz["body"]["bottom"], LAYOUT_H + 0.5, where + "the body stays inside the layout viewport with the keyboard gone under a zoom: %r" % (dz,))
        self.assertLessEqual(dz["composerBottom"], LAYOUT_H - bar_h + 0.5, where + "the composer row is reachable, above the bar's strip: %r" % (dz,))
        self.assertEqual(_px(dz["appTop"]), 0, where + "the held pan is clamped to the viewport: %r" % (dz,))
        self.assertAlmostEqual(zb["composerBottom"], rest["composerBottom"], delta=0.5, msg=where + "%r" % (zb,))
        return r

    def test_chromium_phone_keyboard_pan_leaves_no_band(self):
        self._leg("chromium")

    # WebKit is Safari's engine; an `optional:` skip where the browser is absent (CI installs Chromium alone)
    def test_webkit_phone_keyboard_pan_leaves_no_band(self):
        self._leg("webkit")


if __name__ == "__main__":
    unittest.main()
