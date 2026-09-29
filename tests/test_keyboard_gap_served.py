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
block is the viewport, not the fixed body). On the base tree the composer stops 83 px short of the band. The author's pass 3
(2026-09-19): with the visual viewport dragged to the layout viewport's bottom (offsetTop 336, the band 336..844) the fixed
bar is INSIDE the band, so its strip is reserved and the composer sits above the bar; the first cut of kbOpen took upstream's
height difference first and collapsed the strip, and the bar painted over the composer's bottom. The author's pass 4 (2026-09-20): the
strip is the part of the bar's box inside the band the shell published, so at an interior pan (offsetTop 320, the band
320..828) --mtabs-h is the overlap and the composer sits flush above the bar's visible part; and a pinch over the deep
pan keeps the strip, the bar being inside the published band whatever the height difference says. The author's pass 6 (2026-09-20): the
overlap is of two intervals, so a short band panned deep (20 at 830: 830..850), its top below the bar's top, reserves the
bar's pixels from the band's top down, not the whole bar.

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
# ...and that root's per-session hosts off (the Testing rule for a test that mints its own state root, 2026-09-11): nothing
# resolves this root as STATE today (the lab kernel's root is floored by kernel_env), so this is the belt for the load the
# comment above anticipates, not a fix for anything the module runs now
os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), exist_ok=True)
Path(os.environ["XDG_STATE_HOME"], "romp", "session-hosts").write_text("off\n")

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

    def _drive(self, engine, context=None, tag=""):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        cfg = {"engine": engine, "url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token),
               "healthz": "http://127.0.0.1:%d/healthz" % self.port, "bootTimeoutMs": 30000, "settleMs": 500,
               "context": context,   # None: the phone (the iPhone 14 descriptor at 390 by 844); else a device (or null) and a viewport
               "shots": os.path.join(self.lab, "kb-gap-" + engine + tag) if os.environ.get("KB_GAP_SHOTS") else ""}
        cfg_path = os.path.join(self.lab, "cfg-%s%s.json" % (engine, tag))
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
                        ("kbUpDeep", r["kbUpDeep"]), ("deepZoomed", r["deepZoomed"]), ("kbUpMid", r["kbUpMid"]), ("kbUpLightZoom", r["kbUpLightZoom"]),
                        ("pinchPanned", r["pinchPanned"]), ("kbDownZoomed", r["kbDownZoomed"]), ("kbUpAgainZoomed", r["kbUpAgainZoomed"])):
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
        # the new-session picker lifted under the same keyboard and pan (the author's pass 2, 2026-09-19): the lift is the other fixed box
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
        # the author's pass 9 (2026-09-20), the maintainer's round 5 ruling: the keyboard raised under a LIGHT zoom with no hold standing. The author's pass
        # 8's derived cut (1.0006 at 844) put every scale between it and the old literal 1.01 on the hold road, and with the hold 0
        # (the state after any rest at scale 1) that road published 0px: the band under the composer, the defect this leg exists to
        # close, back under a zoom the eye cannot see. The measured road publishes the pan a pure zoom cannot explain, the measured
        # pixels less the zoom's share L(1 - 1/s) in pixels, derived here from the driven scale (the kernel's derivation sits beside
        # its zoomPx helper); the composer then sits within that share of its resting distance from the band's bottom
        lz, lz_back = r["kbUpLightZoom"], r["settledLight"]
        share = LAYOUT_H * (1 - 1 / 1.003)
        self.assertEqual(lz["vv"]["scale"], 1.003, where + "the shell read the light zoom: %r" % (lz["vv"],))
        self.assertTrue(0 < round(share) <= 8, where + "a light zoom's share is a few pixels: %r" % (share,))
        self.assertEqual(_px(lz["appH"]), KB_H, where + "--app-h is the band's unzoomed height under the light zoom: %r" % (lz,))
        self.assertEqual(_px(lz["appTop"]), 84 - round(share), where + "the keyboard's pan less the zoom's share, not the hold (0): %r" % (lz,))
        lz_band_bottom = 83.7 + 506.48
        self.assertAlmostEqual(lz_band_bottom - lz["composerBottom"], rest_gap, delta=share + 1,
                               msg=where + "the composer keeps its distance from the band's bottom to within the zoom's share plus the rounding pixel (the derived bound), no band: %r" % (lz,))
        self.assertAlmostEqual(lz_back["composerBottom"], rest["composerBottom"], delta=0.5, msg=where + "%r" % (lz_back,))
        # the visual viewport at the layout viewport's bottom with the keyboard up (the author's pass 3, 2026-09-19): the band is 336..844,
        # the fixed bottom:0 bar is inside it, and the fixed body, at the pan, ends where the bar does. The bar's box decides:
        # visible, so its strip is reserved and the composer sits above the bar at its resting distance. The first cut read
        # upstream's height difference first (844 - 508 > 120) and collapsed the strip, so the composer's bottom sat under
        # the bar's whole height.
        deep, deep_back = r["kbUpDeep"], r["settledDeep"]
        self.assertEqual(_px(deep["appTop"]), 336, where + "the pan is published: %r" % (deep,))
        self.assertEqual(_px(deep["appH"]), KB_H, where + "%r" % (deep,))
        self.assertAlmostEqual(deep["body"]["bottom"], LAYOUT_H, delta=0.5, msg=where + "the body ends at the band's bottom, the layout viewport's: %r" % (deep,))
        self.assertAlmostEqual(deep["bar"]["bottom"], LAYOUT_H, delta=0.5, msg=where + "the bar is inside the band: %r" % (deep,))
        self.assertEqual(deep["bar"]["display"], "flex", where + "%r" % (deep,))
        self.assertEqual(_px(deep["mtabsH"]), bar_h, where + "a bar inside the band keeps its strip: %r" % (deep,))
        self.assertAlmostEqual((LAYOUT_H - bar_h) - deep["composerBottom"], rest_gap, delta=1,
                               msg=where + "the composer sits above the bar at its resting distance, not under it: %r" % (deep,))
        # the author's pass 4 (2026-09-20): a PINCH over the deep pan. The shell publishes the same band (the pan holds at 336, --app-h is
        # 254 * 2) and the bar is inside it, so the strip stands and the composer keeps its place above the bar. The author's pass 3
        # reading handed a pinch back to upstream's height difference (844 - 508 > 120: a keyboard) and collapsed the strip
        # at the pinch cut (then the literal 1.01), so the bar painted over the composer's bottom for as long as the zoom held.
        dzm = r["deepZoomed"]
        self.assertEqual(dzm["vv"]["scale"], 2, where + "the shell read the zoom: %r" % (dzm["vv"],))
        self.assertEqual((_px(dzm["appTop"]), _px(dzm["appH"])), (336, KB_H), where + "zoomed over the deep pan, the pan holds and --app-h is the scaled height: %r" % (dzm,))
        self.assertEqual(_px(dzm["mtabsH"]), bar_h, where + "the strip stands under the zoom: the bar is inside the band the shell published: %r" % (dzm,))
        self.assertAlmostEqual((LAYOUT_H - bar_h) - dzm["composerBottom"], rest_gap, delta=1,
                               msg=where + "the composer sits above the bar under the zoom, not under it: %r" % (dzm,))
        self.assertAlmostEqual(deep_back["composerBottom"], rest["composerBottom"], delta=0.5, msg=where + "%r" % (deep_back,))
        # the author's pass 4 (2026-09-20): the pan at an INTERIOR position, the bar partly inside the band (the band 320..828 against a bar
        # whose box starts at 844 less its height). The strip is the part of the bar inside the band, so the composer sits flush
        # above the bar's visible part; the author's pass 3 strip was the bar's whole height there, a dark band between the composer
        # and the keyboard of the height the keyboard hides. The step must be interior (derived from the bar's measured box),
        # or the assertion says nothing about the range.
        mid, mid_back = r["kbUpMid"], r["settledMid"]
        self.assertEqual(_px(mid["appTop"]), 320, where + "the pan is published: %r" % (mid,))
        self.assertEqual(_px(mid["appH"]), KB_H, where + "%r" % (mid,))
        mid_band_bottom = 320 + KB_H
        # the overlap of the two intervals, derived from the box and the band (the author's pass 6, 2026-09-20: it had been the bar's pixels
        # above the band's bottom, the one-edge form, which agrees here and could not disagree anywhere)
        overlap = max(0, min(mid["bar"]["bottom"], mid_band_bottom) - max(mid["bar"]["top"], 320))
        self.assertGreater(overlap, 0.5, where + "the step is interior: the bar's top is above the band's bottom: %r" % (mid,))
        self.assertLess(overlap, bar_h - 0.5, where + "the step is interior: the bar is not wholly inside the band: %r" % (mid,))
        self.assertAlmostEqual(_px(mid["mtabsH"]), overlap, delta=0.5, msg=where + "the strip is the part of the bar inside the band, not its whole height: %r" % (mid,))
        self.assertAlmostEqual(mid_band_bottom - _px(mid["mtabsH"]) - mid["composerBottom"], rest_gap, delta=1,
                               msg=where + "the composer sits above the bar's visible part at its resting distance, no band between them: %r" % (mid,))
        self.assertAlmostEqual(mid_back["composerBottom"], rest["composerBottom"], delta=0.5, msg=where + "%r" % (mid_back,))
        # the author's pass 6 (2026-09-20): the band's TOP edge. A short band panned deep (height 20 at offsetTop 830: 830..850 against the
        # bar's box) has its top below the bar's top and is shorter than the bar, so the strip is the overlap of the two
        # intervals, the bar's pixels from the band's top down to the bar's bottom, derived from the box and the band. The
        # first proportional form read the band's bottom edge only and reserved the whole bar there, more than the band holds.
        sd, sd_back = r["kbUpShortDeep"], r["settledShort"]
        self.assertEqual((_px(sd["appTop"]), _px(sd["appH"])), (830, 20), where + "the short band is published: %r" % (sd,))
        self.assertGreater(830, sd["bar"]["top"], where + "the state: the band's top is below the bar's top: %r" % (sd,))
        self.assertLess(20, bar_h, where + "the state: the band is shorter than the bar: %r" % (sd,))
        sd_overlap = max(0, min(sd["bar"]["bottom"], 830 + 20) - max(sd["bar"]["top"], 830))
        self.assertTrue(0.5 < sd_overlap < bar_h - 0.5, where + "the step is interior: %r against the bar %r" % (sd_overlap, sd["bar"]))
        self.assertAlmostEqual(_px(sd["mtabsH"]), sd_overlap, delta=0.5, msg=where + "the strip is the overlap of the band and the bar's box, not the bar's pixels above the band's bottom: %r" % (sd,))
        self.assertAlmostEqual(sd_back["composerBottom"], rest["composerBottom"], delta=0.5, msg=where + "%r" % (sd_back,))
        # a pinch after the pan, and the keyboard dismissed while zoomed (the author's pass 2, 2026-09-19): zoomed with the keyboard up the
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
        # the author's pass 4 (2026-09-20): the keyboard raised AGAIN under the same zoom. The clamp bounded what the run above published and
        # left the hold standing, so the pan is 83 again and the body is the band; a clamp that wrote back had lowered the
        # hold to 0 and laid the body out at 0..508 under the pan, the band reopened for as long as the zoom held.
        uz = r["kbUpAgainZoomed"]
        self.assertEqual((_px(uz["appTop"]), _px(uz["appH"])), (KB_PAN, KB_H), where + "the hold survives the clamp: %r" % (uz,))
        self.assertAlmostEqual(uz["body"]["top"], KB_PAN, delta=0.5, msg=where + "the body is back at the pan under the zoom: %r" % (uz,))
        self.assertAlmostEqual(uz["body"]["bottom"], band_bottom, delta=0.5, msg=where + "%r" % (uz,))
        self.assertAlmostEqual(zb["composerBottom"], rest["composerBottom"], delta=0.5, msg=where + "%r" % (zb,))
        self._hold(r, where, rest_gap)
        return r

    def _hold(self, r, where, rest_gap):
        """The maintainer's round 6 ruling (2026-09-29), served: the pinch road's hold. Under a real pinch a drag or a continuous pinch
        had overwritten a standing hold (a drag one pixel past the zoom's share dropped 83 to 1, a continuous pinch lowered it at every
        step, a drag to 590 at scale 2 stored 168 for the re-raise), a hold of 0 read as none, and a keyboard raised again with no pan
        published the stale hold (the composer 81.5 px below the visible band's bottom under a zoom of 1.003; 167.7 and 337 px at
        scales 1.2 and 2). Since the same ruling a pan of a keyboard raised at this zoom follows the reading (a pan to the share
        after a no-pan re-raise at 1.05 had left a band of 16 px under the composer), re-bounded from the larger of the hold and the
        value in force (a pan back up after a deep re-raise at scale 2 had published the hold, 83, and left a band of 85 px), a
        keyboard swapped in at that zoom is a pan on its own run, so a refit at the swap's report publishes what the swap's run did
        (it had published 236 and then 40), and a pan after a zoom alone keeps the hold (the stance). The values are the rules
        test_kernel_mobile.MobileFitExecutes derives cell by cell; here the served shell publishes them and lays the body and the
        composer out at them. Every cell is checked before the leg fails."""
        cells = r["r6"]
        self.assertEqual(len(cells), 79, where + "the driver ran every cell: %r" % ([(c["fam"], c["tag"]) for c in cells],))
        top = {(c["fam"], c["tag"]): _px(c["g"]["appTop"]) for c in cells}
        want = {}
        for fam in ("drag423", "drag590"):
            want.update({(fam, "kbUp"): 83, (fam, "pinch2"): 83, (fam, "back"): 83, (fam, "kbDownZ"): 0, (fam, "reRaiseZ"): 83})
        want[("drag423", "drag")] = 83                 # one pixel past the share (422): the hold, not the 1 px excess
        want[("drag590", "drag")] = 590 - 422          # past the hold plus the share: the excess, published and not stored
        want.update({("pinch", c["tag"]): 83 for c in cells if c["fam"] == "pinch" and c["tag"].startswith("s")})
        want.update({("pinch", "kbUp"): 83, ("pinch", "kbDownZ"): 0, ("pinch", "reRaiseZ"): 83})
        want.update({("lz1.003", "kbDown"): 0, ("lz1.003", "kbUpNoPan"): 0, ("hold83-lz1.003", "kbUp"): 83,
                     ("hold83-lz1.003", "kbDown"): 0, ("hold83-lz1.003", "kbUpNoPan"): 0})
        want[("lz1.003", "kbUpPan")] = KB_PAN - round(LAYOUT_H * (1 - 1 / 1.003))   # no hold: the reading (83) less the share (3)
        for fam, excess in (("hold0-1.05", 40), ("hold0-2", 590 - 422)):
            want.update({(fam, "kbUp0"): 0, (fam, "pinchC"): 0, (fam, "drag"): excess, (fam, "back0"): 0, (fam, "down"): 0, (fam, "reNoPan"): 0})
        for fam in ("reraise-s1.2", "reraise-s2"):
            want.update({(fam, "kbUp1"): 83, (fam, "pinchC"): 83, (fam, "down1"): 0, (fam, "reNoPan"): 0, (fam, "down2"): 0, (fam, "reSameP"): 83})
        share105 = round(LAYOUT_H * (1 - 1 / 1.05))   # the zoom's share at 1.05 in pixels, 40
        want.update({("lz1.05", "kbUpPan"): KB_PAN - share105, ("lz1.05", "kbDown"): 0, ("lz1.05", "kbUpNoPan"): 0,
                     ("lz1.05", "panInShare"): min(KB_PAN - share105, share105)})   # the pan rule: the hold (43) bounded into [0, 40]
        want.update({("stance", t): 83 for t in ("kbUp", "at200", "up40", "at0")})   # the stance: a zoom alone since the raise
        share2 = round(LAYOUT_H * (1 - 1 / 2))   # the zoom's share at scale 2 in pixels, 422
        want.update({("reraiseDeep2", "kbUp"): KB_PAN, ("reraiseDeep2", "kbDownZ"): 0,
                     ("reraiseDeep2", "reRaiseDeep"): 590 - share2,                    # the re-raise bound: the reading less the share, 168
                     ("reraiseDeep2", "panUp"): min(max(KB_PAN, 590 - share2), 422)})  # the pan rule: the larger of 83 and 168, capped at the reading
        want.update({("swapRefit2", "kb471up"): round(657.5) - share2,                 # the raise under the zoom: the reading less the share, 236
                     ("swapRefit2", "swap508"): min(round(657.5) - share2, 40),        # the swap, a pan: 236 bounded into the reading's [0, 40]
                     ("swapRefit2", "refit"): min(round(657.5) - share2, 40)})         # the refit at the same report: the same value
        self.assertEqual(sorted(k for k in top if k[1] != "rest"), sorted(want), where + "every cell has its expected value")
        bad = ["%s %s: %d, not %d" % (k[0], k[1], top[k], v) for k, v in sorted(want.items()) if top[k] != v]
        for c in cells:
            g, name = c["g"], "%s %s" % (c["fam"], c["tag"])
            if not (g["vv"]["fake"] and g["innerHeight"] == LAYOUT_H and g["scrollY"] == 0 and g["composerBottom"] is not None):
                bad.append(name + ": the emulation did not hold: %r" % (g,))
                continue
            if round(c["h"] * c["sc"]) != KB_H:
                continue
            # the keyboard up: the body is the published band, and the composer sits at its bottom at its resting distance
            t = _px(g["appTop"])
            if abs(g["body"]["top"] - t) > 0.5 or abs(g["body"]["bottom"] - (t + KB_H)) > 0.5:
                bad.append(name + ": the body is not the published band: %r" % (g["body"],))
            if abs((t + KB_H - rest_gap) - g["composerBottom"]) > 1:
                bad.append(name + ": the composer is not at the published band's bottom: %r" % (g,))
            if c["tag"] in ("panInShare", "panUp"):
                # the pan rule: the composer never sits above the visible band's bottom by more than a pixel, the band the kept value left
                # (panInShare) or the hold re-bounded alone left (panUp)
                under = (c["ot"] + c["h"]) - (g["composerBottom"] + rest_gap)
                if under > 1:
                    bad.append(name + ": a band of %.2f px under the composer" % under)
            if c["tag"] in ("kbUpNoPan", "reNoPan"):
                # a keyboard raised with no pan under the zoom: the composer below the visible band's bottom by the zoom's own
                # magnification at most (the band is 508/s tall from the top), never by a stale hold on top of it
                over = g["composerBottom"] + rest_gap - (c["ot"] + c["h"])
                if over > KB_H - c["h"] + 1:
                    bad.append(name + ": the composer sits %.2f px below the visible band's bottom, past the zoom's %.2f" % (over, KB_H - c["h"]))
        if bad:
            self.fail(where + "the pinch road's hold, served; %d cells:\n%s" % (len(bad), "\n".join(bad)))

    def _populations(self, engine):
        """The writer's and the consumer's populations, as the comments in fit() and over the fixed body rule state them (the author's pass
        2, 2026-09-19). fit() publishes a non-zero pan only off a coarse pointer, at any width; the fixed body applies wherever
        _MOBILE_MQ matches: at most 820 px wide at any pointer, or a coarse pointer at most 1024 px wide. The two differ in
        both directions, and each side is driven here in a real engine under the same fake pan as the phone legs."""
        where = engine + ": "
        # a fine pointer at 800 px: inside the query by width alone. The body is fixed, at top 0: the non-coarse branch writes
        # 0px (a pan is a soft-keyboard thing), the height is document.documentElement.clientHeight (innerHeight only where the
        # document element has none, a node stub; the author's pass 9, 2026-09-20: these sites had named innerHeight as the source), so this
        # window lays out exactly as before the pan. This leg does not discriminate the two sources: at 800 by 900 both are 900
        fine = self._drive(engine, {"device": None, "viewport": {"width": 800, "height": 900}}, "-fine800")
        up = fine["kbUp"]
        # the premise first (the author's pass 4, 2026-09-20): every geometric assertion below is satisfied identically by a page whose fake
        # viewport was never installed or never panned (a real, unpanned viewport reads offsetTop 0), so the emulation is
        # pinned the way the phone leg pins it: the fake is what the shell reads, its install raised nothing, and it was panned
        self.assertTrue(up["vv"]["fake"], where + "the shell's visualViewport is the fake: %r" % (up["vv"],))
        self.assertIsNone(up["labVVError"], where + "%r" % (up,))
        self.assertEqual(up["vv"]["offsetTop"], KB_PAN, where + "the fake was panned: %r" % (up["vv"],))
        self.assertEqual((up["innerWidth"], up["coarse"], up["mobile"]), (800, False, True), where + "the emulation held, a fine pointer inside the query: %r" % (up,))
        self.assertEqual(up["body"]["position"], "fixed", where + "the fixed body applies by width alone: %r" % (up,))
        self.assertEqual(_px(up["appTop"]), 0, where + "a fine pointer writes 0px whatever the visual viewport says: %r" % (up,))
        self.assertEqual(_px(up["appH"]), 900, where + "the height is the layout viewport, read as clientHeight, when the pointer is not coarse (innerHeight agrees at this size, so this leg does not tell the two apart): %r" % (up,))
        self.assertAlmostEqual(up["body"]["top"], 0, delta=0.5, msg=where + "%r" % (up,))
        self.assertAlmostEqual(up["body"]["bottom"], 900, delta=0.5, msg=where + "%r" % (up,))
        self.assertEqual(up["bar"]["display"], "flex", where + "the phone layout, by width")
        # the author's pass 6 (2026-09-20): the strip on this road. The band is 0 to the layout viewport (clientHeight), the fixed bar's box is inside it, and the
        # strip is the bar's measured height, the same as at rest: upstream's pointer-ungated kbOpen read the short visual
        # viewport as a keyboard here and collapsed the strip over the composer
        self.assertGreater(_px(fine["rest"]["mtabsH"]), 0, where + "the bar's height is measured at rest: %r" % (fine["rest"],))
        self.assertEqual(_px(up["mtabsH"]), _px(fine["rest"]["mtabsH"]), where + "the strip is the bar's height on a fine pointer whatever the visual viewport says: %r" % (up,))
        # a coarse pointer at 1200 px: outside the query (its coarse term stops at 1024 px). The pan IS published, the writer
        # being pointer-gated, and no rule consumes it: the body stays in flow at layout y 0, sized by --app-h as on every layout
        wide = self._drive(engine, {"device": "iPhone 14", "viewport": {"width": 1200, "height": 900}}, "-coarse1200")
        up = wide["kbUp"]
        self.assertTrue(up["vv"]["fake"], where + "the shell's visualViewport is the fake: %r" % (up["vv"],))
        self.assertIsNone(up["labVVError"], where + "%r" % (up,))
        self.assertEqual(up["vv"]["offsetTop"], KB_PAN, where + "the fake was panned: %r" % (up["vv"],))
        self.assertEqual((up["innerWidth"], up["coarse"], up["mobile"]), (1200, True, False), where + "the emulation held, a coarse pointer outside the query: %r" % (up,))
        self.assertEqual(up["body"]["position"], "static", where + "no fixed body outside the query: %r" % (up,))
        self.assertEqual(_px(up["appTop"]), KB_PAN, where + "the pan is published off a coarse pointer at any width, consumed by nothing here: %r" % (up,))
        self.assertAlmostEqual(up["body"]["top"], 0, delta=0.5, msg=where + "the body stays at layout y 0: %r" % (up,))
        self.assertEqual(up["bar"]["display"], "none", where + "the desktop layout")

    def test_chromium_phone_keyboard_pan_leaves_no_band(self):
        self._leg("chromium")

    # WebKit is Safari's engine; an `optional:` skip where the browser is absent (CI installs Chromium alone)
    def test_webkit_phone_keyboard_pan_leaves_no_band(self):
        self._leg("webkit")

    def test_chromium_the_pan_writer_and_the_fixed_body_cover_the_populations_the_comments_state(self):
        self._populations("chromium")

    def test_webkit_the_pan_writer_and_the_fixed_body_cover_the_populations_the_comments_state(self):
        self._populations("webkit")


if __name__ == "__main__":
    unittest.main()
