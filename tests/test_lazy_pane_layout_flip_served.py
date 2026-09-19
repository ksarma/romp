#!/usr/bin/env python3
"""A lazy pane's failed load judged across an ACTUAL layout flip, in a real engine (review round 3 of the lazy panes, 2026-09-19,
family one: regression-1, extra7-2, kernel-2). The shell's failure detectors are armed on the phone, where the failed state is
painted and a tap retries; a promotion armed there kept judging after a rotation to the desktop, where nothing paints a failure,
and failed() re-parked under data-lazy-src whatever the layout, so a desktop column was left with neither src nor data-src and no
road to promote it again short of a reload. Now failed() reads the layout when the failure is JUDGED: on the desktop the url goes
back to data-src (what the grid's promotion reads), the failed class is cleared and the pane is promoted once more; every promotion
mints the token, so the phone-armed listener and backstop are inert over the desktop's re-promotion.

Driven here across the media query itself (tests/lazy_pane_layout_flip_browser.mjs): page.setViewportSize widens the window past
_MOBILE_MQ's 820 px, so Chromium fires the MediaQueryList change event and the shell's own lazyFlip and retell listeners run, with
mobileOn() the shell's real function over the real query (tests/test_pane_state_broadcast.py LazyPanes drives the same lines under
node with a MediaQueryList fake). Case A fails the pane on the phone and then flips; case B flips WHILE the pane loads and lets the
abort land on the desktop. Chromium alone: WebKit's failure detector is the 30 s backstop (no load event for a failed navigation),
which would cost 30 s a case for the same shell lines the LazyPanes harness covers.

The lab: one kernel from test_ship_reship_served.kernel_env with the return harness's seed (three synthetic sessions of the
notes-api demo plus a transcript-less one; placeholder uuids, host TESTHOST) and a private dist. Skips LOUDLY without the
extension deps or a Chromium (CI installs Chromium and runs the *_served.py files under ROMP_SERVED_TESTS_REQUIRE=1). Synthetic
sessions only; no real data; the lab kernel uses its own port, asserted on /healthz before any request."""
import json
import lab_dist
import os
import shutil
import signal
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
import test_ship_reship_served as _lab                                      # noqa: E402  (kernel_env: every lab kernel's environment)
from test_return_from_background_served import _seed, _free_port, _rows      # noqa: E402  the return harness's lab seed and helpers (functions only, never its TestCase)

# Hermetic state BEFORE anything: this module loads no romp code in-process (the kernel is a subprocess under
# kernel_env's roots), but the floor costs two lines and a later edit that adds a load must not write real state.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

DRIVER = os.path.join(HERE, "lazy_pane_layout_flip_browser.mjs")
HOST = "TESTHOST"


class LazyPaneLayoutFlip(unittest.TestCase):
    """One lab kernel for both cases; each case is one driver run and one artifact under the lab."""
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
        cls.lab = tempfile.mkdtemp(prefix="lazy-flip-")
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)
        cls.state, claude = _seed(cls.lab)
        cls.diag = os.path.join(cls.state, "client-diag.jsonl")
        cls.port, cls.token = _free_port(), "testtok-flip"
        seams = {"ROMP_HOST_NAME": HOST}
        cls.env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token, **seams)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"), stderr=subprocess.STDOUT, env=cls.env)
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

    def _drive(self, case):
        cfg = {"case": case, "url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token), "healthz": "http://127.0.0.1:%d/healthz" % self.port,
               "diag": self.diag, "settleMs": 1200, "holdMs": 1500, "resultPath": os.path.join(self.lab, "result-%s.json" % case)}
        cfg_path = os.path.join(self.lab, "cfg-%s.json" % case)
        Path(cfg_path).write_text(json.dumps(cfg))
        try:
            p = subprocess.run(["node", DRIVER], capture_output=True, text=True, timeout=180, env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg_path))
        except subprocess.TimeoutExpired as e:
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            self.fail("driver timed out; partial output:\n%s" % so[-3000:])
        if p.returncode == 3:
            self.skipTest("no playwright chromium on this box: the served leg needs one (CI installs it)")
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        r = json.loads(line[len("RESULT:"):])
        self.assertNotIn("died", r, "driver aborted early: %r (kernel log tail: %s)" % (r.get("died"), Path(self.klog).read_text()[-800:]))
        self.assertEqual(sorted(r.get("bootUp") or []), ["chat", "feed"], "the phone's two eager panes came up before the tap: %r" % (r.get("bootUp"),))
        b = r.get("boot") or {}
        self.assertEqual((b.get("mobile"), b.get("src"), b.get("lazy")), (True, None, "/waiting"), "the phone layout, the Waiting pane parked at boot: %r" % (b,))
        return r

    def test_A_a_failure_on_the_phone_is_handed_to_the_desktop_as_a_promotion_and_the_flip_back_shows_a_loaded_pane(self):
        r = self._drive("A")
        pf = r["phoneFailed"]
        self.assertGreaterEqual(pf.get("ms", -1), 0, "the aborted fetch's error page fired load and the shell painted the failed state on the phone: %r" % (pf,))
        self.assertEqual((pf["mobile"], pf["src"], pf["lazy"], pf["divFailed"], pf["bodyFailed"]), (True, None, "/waiting", True, True), "re-parked under data-lazy-src, the failed state up: %r" % (pf,))
        d = r["desktop"]
        self.assertGreaterEqual(d.get("ms", -1), 0, "after the widen the pane's document loaded and painted on the desktop within the wait: %r" % (d,))
        self.assertEqual((d["mobile"], d["src"], d["lazy"], d["dataSrc"]), (False, "/waiting", None, "/waiting"), "the flip ran the shell's lazyFlip: the parked url handed back to data-src, the pane promoted (before this the phone's park left the desktop column with neither): %r" % (d,))
        self.assertEqual((d["divFailed"], d["bodyFailed"], d["divLoading"], d["bodyLoading"]), (False, False, False, False), "no failed or loading state on the desktop (the promotion clears the phone's failed class): %r" % (d,))
        self.assertTrue(d["url"].endswith("/waiting") and d["spinGone"] and d["head"], "the frame's document is the Waiting page, painted (its own loader retired, its head element present): %r" % (d,))
        self.assertEqual(d["sets"], 2, "two src sets: the phone's tap and the desktop's promotion: %r" % (d,))
        pa = r["phoneAgain"]
        self.assertEqual((pa["mobile"], pa["src"], pa["divFailed"], pa["bodyFailed"], pa["bodyLoading"], pa["display"], pa["sets"]), (True, "/waiting", False, False, False, "block", 2), "back on the phone the tab shows the loaded pane: no failed overlay over a working pane (the round-2 refuter's rotate-and-back road), no third promotion: %r" % (pa,))
        self.assertEqual([x for x in r["rows"] if x["what"] == "pane-load-failed"], [{"what": "pane-load-failed", "pane": "waiting", "via": "load", "n": 1}], "one failure row, the phone's: %r" % (r["rows"],))
        self.assertEqual([x for x in r["rows"] if x["what"] == "pane-load-unmarked"], [], "the desktop's load was the pane's own document, not an unmarked one")
        self.assertEqual(r["errors"], [], "no page errors")

    def test_B_a_failure_judged_after_a_flip_mid_load_re_promotes_on_the_desktop_once_and_the_phone_armed_detectors_are_inert(self):
        r = self._drive("B")
        ml = r["midLoad"]
        self.assertEqual((ml["mobile"], ml["src"], ml["divLoading"], ml["bodyLoading"], ml["sets"]), (True, "/waiting", True, True, 1), "the phone tap: loading, the listener and backstop armed on the phone: %r" % (ml,))
        fl = r["flippedLoading"]
        self.assertEqual((fl["mobile"], fl["src"], fl["sets"]), (False, "/waiting", 1), "the flip mid-load: the desktop, the phone's promotion standing (lazyFlip refuses a pane with a src), no second set yet: %r" % (fl,))
        d = r["desktop"]
        self.assertGreaterEqual(d.get("ms", -1), 0, "the abort landed on the desktop, the shell re-promoted, the real document loaded and painted within the wait: %r" % (d,))
        self.assertEqual((d["src"], d["lazy"], d["dataSrc"], d["divFailed"], d["bodyFailed"]), ("/waiting", None, "/waiting", False, False), "failed() read the desktop: the url back under data-src, promoted again, no failed class (before: neither src nor data-src): %r" % (d,))
        self.assertTrue(d["url"].endswith("/waiting") and d["spinGone"] and d["head"], "the re-promotion's document is the Waiting page, painted: %r" % (d,))
        a = r["after"]
        self.assertEqual((a["sets"], a["src"], a["divFailed"]), (2, "/waiting", False), "exactly two promotions (the tap's and the desktop's): no third, the phone's listener and backstop being inert on their stale token: %r" % (a,))
        self.assertEqual(len(r["requests"]), 2, "two document requests for /waiting reached the wire (the aborted one and the real one): %r" % (r["requests"],))
        self.assertEqual(r["routeHeld"], 2, "the route saw the held-then-aborted request and one that passed: %r" % (r["routeHeld"],))
        self.assertEqual([x for x in r["rows"] if x["what"] == "pane-load-failed"], [{"what": "pane-load-failed", "pane": "waiting", "via": "load", "n": 1}], "one failure row via load, the desktop-judged one: %r" % (r["rows"],))
        self.assertEqual(r["errors"], [], "no page errors")

    def test_C_when_the_desktop_re_promotion_fails_too_the_browsers_page_stands_and_nothing_promotes_a_third_time(self):
        # extra7-2's refuter: with the token minted on the phone alone, the phone-armed listener also judged the desktop's second failure and the
        # promote-fail cycle ran until the route passed. The desktop promotion arms no listener and no backstop, so a second failure there shows
        # the browser's own page (as before this change) with the url under data-src; the token minted per promotion keeps the phone's listener
        # inert over it, so exactly two document requests reach the wire and two src sets happen, whatever the route would do to a third.
        r = self._drive("C")
        d = r["desktop"]
        self.assertGreaterEqual(d.get("ms", -1), 0, "the desktop's re-promotion reached the wire within the wait: %r" % (d,))
        self.assertEqual((d["src"], d["lazy"], d["dataSrc"], d["divFailed"], d["bodyFailed"]), ("/waiting", None, "/waiting", False, False), "the desktop-judged failure: the url under data-src, promoted again, no failed state: %r" % (d,))
        a = r["after"]
        self.assertEqual((a["sets"], a["src"], a["dataSrc"], a["divFailed"], a["divLoading"]), (2, "/waiting", "/waiting", False, False), "three seconds on: two promotions and no third (the phone's listener is inert on its stale token over the desktop's re-promotion; without the per-promotion mint it judged the second failure and promoted again): %r" % (a,))
        self.assertIsNone(a["url"], "the browser's own error page stands in the frame (cross-origin, no readable document), as a desktop failure always did: %r" % (a,))
        self.assertEqual(len(r["requests"]), 2, "two document requests reached the wire, both aborted; no third: %r" % (r["requests"],))
        self.assertEqual(r["routeHeld"], 2, "the route saw exactly the two: %r" % (r["routeHeld"],))
        self.assertEqual([x for x in r["rows"] if x["what"] == "pane-load-failed"], [{"what": "pane-load-failed", "pane": "waiting", "via": "load", "n": 1}], "one failure row: the phone-armed detector's; the desktop's own failure is the browser's page, unsaid: %r" % (r["rows"],))
        self.assertEqual(r["errors"], [], "no page errors")


if __name__ == "__main__":
    unittest.main()
