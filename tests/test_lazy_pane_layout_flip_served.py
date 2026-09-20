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
abort land on the desktop; case C fails the desktop's re-promotion too and, back on the phone, recovers by one of the three gestures
(review round 4: the desktop promotion has its own detectors, its failure is bounded to one re-promotion per episode, and the flip back
parks the recorded pane with the failed state); case D drives the kernel's own 403 to the desktop's bound, where the document the kernel sent
is dropped from the frame (pass 5, the author's label, taking the reviewer's round-4 finding correctness-3); case E holds a desktop load past the 30 s backstop and lets it land on the kept src
(pass 5, the reviewer's round-4 findings tests-2 with extra9-1). Chromium alone: WebKit's failure detector is the 30 s backstop (no load event for a
failed navigation), which would cost 30 s a case for the same shell lines the LazyPanes harness covers.

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

    def _drive(self, case, recover=None):
        cfg = {"case": case, "recover": recover or "", "url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token), "healthz": "http://127.0.0.1:%d/healthz" % self.port,
               "diag": self.diag, "settleMs": 1200, "holdMs": 1500, "slowMs": 34000, "resultPath": os.path.join(self.lab, "result-%s%s.json" % (case, "-" + recover if recover else ""))}
        cfg_path = os.path.join(self.lab, "cfg-%s%s.json" % (case, "-" + recover if recover else ""))
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

    def _case_c(self, recover):
        # review round 4 (2026-09-19, regression-1 with correctness-1 and extra6-1: one defect). At round 3's head the desktop promotion armed no
        # listener and no backstop, so when the desktop's re-promotion failed too the pane kept a src over the browser's error page with no
        # state, lazyFlip's flip-back parking skipped a frame with a src, and back on the phone the tab tap, the overlay tap and the Try again
        # button all did nothing for the page's life (the parent commit recovered from the same sequence). Now every promotion arms both
        # detectors; the desktop's response is bounded to one re-promotion per episode (the src kept at the bound, the browser's own page as a
        # desktop failure always showed, the failure recorded), and the flip back parks the recorded pane with the failed state, from which
        # each of the three gestures promotes it again. Driven three times, one gesture per run (recover), in Chromium against the lab kernel.
        r = self._drive("C", recover)
        d = r["desktop"]
        self.assertGreaterEqual(d.get("ms", -1), 0, "the desktop's re-promotion reached the wire within the wait: %r" % (d,))
        self.assertEqual((d["src"], d["lazy"], d["dataSrc"], d["divFailed"], d["bodyFailed"]), ("/waiting", None, "/waiting", False, False), "the desktop-judged failure: the url under data-src, promoted again, no failed state: %r" % (d,))
        a = r["after"]
        self.assertEqual((a["sets"], a["src"], a["dataSrc"], a["divFailed"], a["divLoading"], a["mobile"]), (2, "/waiting", "/waiting", False, False, False), "three seconds on: two promotions and no third (the episode's bound; the phone's listener is inert on its stale token; without the bound the desktop's own detector would promote, fail, promote): %r" % (a,))
        self.assertIsNone(a["url"], "the browser's own error page stands in the frame at the bound (cross-origin, no readable document), as a desktop failure always did: %r" % (a,))
        self.assertEqual(r["requestsAtBound"], 2, "two document requests reached the wire before the flip back, both aborted; no third: %r" % (r["requests"],))
        pb = r["phoneBack"]
        self.assertGreaterEqual(pb.get("ms", -1), 0, "the flip back parked the recorded pane within the wait: %r" % (pb,))
        self.assertEqual((pb["mobile"], pb["src"], pb["lazy"], pb["dataSrc"], pb["divFailed"], pb["bodyFailed"], pb["bodyLoading"], pb["sets"]), (True, None, "/waiting", None, True, True, False, 2),
                         "back on the phone: no src over the dead document, the url under data-lazy-src, the failed state painted over the shown Waiting tab (at round 3's head: the src stood, no state, every road dead): %r" % (pb,))
        self.assertEqual(pb["msg"], "Still not loading. Try again, or reload the page.", "the episode's copy (two failures in it): %r" % (pb,))
        rb = pb.get("retry") or {}
        self.assertEqual((rb.get("hidden"), rb.get("text")), (False, "Try again"), "the button is shown: %r" % (rb,))
        self.assertNotEqual(rb.get("display"), "none", "...and painted: %r" % (rb,))
        rec = r["recovered"]
        self.assertGreaterEqual(rec.get("ms", -1), 0, "the %s gesture promoted the pane again and its document loaded and painted within the wait: %r" % (recover, rec))
        self.assertEqual((rec["mobile"], rec["src"], rec["lazy"], rec["divFailed"], rec["bodyFailed"], rec["bodyLoading"], rec["sets"]), (True, "/waiting", None, False, False, False, 3), "the third promotion, by the %s gesture: the pane loaded, the failed state gone: %r" % (recover, rec))
        self.assertTrue(rec["url"].endswith("/waiting") and rec["spinGone"] and rec["head"], "its document is the Waiting page, painted: %r" % (rec,))
        self.assertEqual(len(r["requests"]), 3, "three document requests in all: the two aborted and the one that passed: %r" % (r["requests"],))
        self.assertEqual(r["routeHeld"], 3, "the route saw exactly the three: %r" % (r["routeHeld"],))
        self.assertEqual([x for x in r["rows"] if x["what"] == "pane-load-failed"], [{"what": "pane-load-failed", "pane": "waiting", "via": "load", "n": 1}, {"what": "pane-load-failed", "pane": "waiting", "via": "load", "n": 2}],
                         "two failure rows: the phone-armed detector's and the desktop's own (round 3 left the second unsaid); the recovery filed none: %r" % (r["rows"],))
        self.assertEqual([x for x in r["rows"] if x["what"] == "pane-load-unmarked"], [], "nothing was shown as served")
        self.assertEqual(r["errors"], [], "no page errors")

    def test_C_when_the_desktop_re_promotion_fails_too_the_flip_back_parks_it_with_the_failed_state_and_the_tab_tap_recovers(self):
        self._case_c("tab")

    def test_C_when_the_desktop_re_promotion_fails_too_the_overlay_tap_recovers(self):
        self._case_c("overlay")

    def test_C_when_the_desktop_re_promotion_fails_too_the_try_again_button_recovers(self):
        self._case_c("button")

    def test_D_at_the_desktop_bound_the_kernels_own_denial_is_dropped_from_the_frame_and_the_flip_back_parks_it_with_the_failed_state(self):
        # pass 5, the author's label (2026-09-20, taking the reviewer's round-4 finding correctness-3, ruled high): the desktop's bound is reached by docState's `other` answer too, whose commonest
        # member is the kernel's own 403 line (its body names the serve-token file's path). Round 4's bound kept the src whatever the answer, so
        # that body stood on the desktop's screen with no failed state and no retry for the page's life. Driven against the REAL kernel's denial
        # (the route re-issues the request credential-less and hands the frame the kernel's answer): at the bound the src is dropped and the frame
        # navigates to about:blank (the kernel's answer is on show for the frames between its commit and the load event that judged it, then
        # dropped: the author's pass-5 verify's rAF witness saw it for about two frames), the url waits under data-lazy-src, the attribute the
        # controller's gear-save reconcile does not read (under data-src it re-fetched the denial on every save with no token and no backstop,
        # the author's pass-5 verify; the Waiting pane is outside that controller's optional set, so the reconcile road is driven by the LazyPanes node
        # case on the Outline, where a save after the bound moves nothing), no third request; the flip back parks it with the failed state and
        # the tab tap loads it. Asserted: the status and the page's state. The body is never read, printed or kept by the driver or here.
        r = self._drive("D")
        d = r["desktopBound"]
        self.assertGreaterEqual(d.get("ms", -1), 0, "the second denial reached the bound within the wait (two promotions, then the src dropped): %r" % (d,))
        self.assertEqual((d["mobile"], d["src"], d["lazy"], d["dataSrc"], d["sets"]), (False, None, "/waiting", None, 2), "the desktop's bound over a document the kernel sent: the src DROPPED, the url under data-lazy-src (not data-src: the controller's reconcile reads that on every gear save), two promotions (before: the src kept over the 403 body): %r" % (d,))
        self.assertEqual((d["divFailed"], d["bodyFailed"], d["divLoading"], d["bodyLoading"]), (False, False, False, False), "no failed or loading state on the desktop (nothing paints one there): %r" % (d,))
        b = r["blanked"]
        self.assertGreaterEqual(b.get("ms", -1), 0, "the frame navigated to about:blank once the src was dropped: the kernel's answer, on show for the frames between its commit and the load event that judged it, is dropped: %r" % (b,))
        self.assertEqual(b["url"], "about:blank", "%r" % (b,))
        self.assertEqual(r["denied"], {"statuses": [403, 403], "responses": 2}, "the kernel answered both document requests with its 403 (the status read off the response; the body never read): %r" % (r["denied"],))
        a = r["after"]
        self.assertEqual((a["sets"], a["src"], a["lazy"], a["dataSrc"], a["url"]), (2, None, "/waiting", None, "about:blank"), "1.5 s on: no third promotion, the frame blank: %r" % (a,))
        self.assertEqual(r["requestsAtBound"], 2, "two document requests reached the wire before the flip back, both denied; no third: %r" % (r["requests"],))
        pb = r["phoneBack"]
        self.assertGreaterEqual(pb.get("ms", -1), 0, "the flip back parked the recorded pane within the wait: %r" % (pb,))
        self.assertEqual((pb["mobile"], pb["src"], pb["lazy"], pb["dataSrc"], pb["divFailed"], pb["bodyFailed"], pb["sets"]), (True, None, "/waiting", None, True, False, 2), "back on the phone: the src-less pane parked under data-lazy-src with the failed state on its div (the chat is the shown tab, so nothing is painted yet): %r" % (pb,))
        rec = r["recovered"]
        self.assertGreaterEqual(rec.get("ms", -1), 0, "the Waiting tab's tap promoted the pane again and its document loaded and painted within the wait: %r" % (rec,))
        self.assertEqual((rec["mobile"], rec["src"], rec["lazy"], rec["divFailed"], rec["bodyFailed"], rec["bodyLoading"], rec["sets"]), (True, "/waiting", None, False, False, False, 3), "the third promotion, by the tab tap: the pane loaded, the failed state gone: %r" % (rec,))
        self.assertTrue(rec["url"].endswith("/waiting") and rec["spinGone"] and rec["head"], "its document is the Waiting page, painted: %r" % (rec,))
        self.assertEqual((len(r["requests"]), r["routePassed"]), (3, 1), "three document requests in all: the two denied and the one that passed: %r" % (r["requests"],))
        self.assertEqual([x for x in r["rows"] if x["what"] == "pane-load-failed"], [{"what": "pane-load-failed", "pane": "waiting", "via": "load", "n": 1}, {"what": "pane-load-failed", "pane": "waiting", "via": "load", "n": 2}],
                         "two failure rows via load (the 403 commits a document and fires load); the recovery filed none: %r" % (r["rows"],))
        self.assertEqual([x for x in r["rows"] if x["what"] == "pane-load-unmarked"], [], "nothing was shown as served")
        self.assertEqual(r["errors"], [], "no page errors")

    def test_E_a_slow_desktop_load_is_held_through_the_backstop_and_lands_on_the_kept_src(self):
        # pass 5, the author's label (2026-09-20, taking the reviewer's round-4 findings tests-2 with extra9-1): every desktop promotion arms the 30 s backstop since pass 4, and its `blank` answer
        # (a fetch not yet committed) was a failure there too, so a healthy but slow desktop load was torn down at 30 s, re-fetched, and filed a
        # row (the LazyPanes node cases drive the same lines and the rotation back). Here the Waiting pane's one request is held 34 s by the route
        # and then answered by the lab kernel: at the backstop the src is kept and nothing is re-fetched (one request on the wire, one src set),
        # the row records the 30 s uncommitted document, and the document lands on the kept src and paints.
        r = self._drive("E")
        fl = r["flipped"]
        self.assertEqual((fl["mobile"], fl["src"], fl["lazy"], fl["dataSrc"], fl["sets"], fl["url"]), (False, "/waiting", None, "/waiting", 1, "about:blank"), "the rotation to the desktop promoted the parked pane; its request is held, the frame's document still the initial about:blank: %r" % (fl,))
        ab = r["atBackstop"]
        self.assertGreaterEqual(ab["atMs"], 30000, "the read is past LOAD_MS: %r" % (ab,))
        self.assertEqual((ab["src"], ab["lazy"], ab["dataSrc"], ab["sets"], ab["url"]), ("/waiting", None, "/waiting", 1, "about:blank"), "the HOLD: past the backstop the src is kept and nothing was re-fetched (one set; round 4: the src dropped and a second promotion): %r" % (ab,))
        self.assertEqual((ab["divFailed"], ab["bodyFailed"], ab["divLoading"], ab["bodyLoading"]), (False, False, False, False), "no failed or loading state on the desktop: %r" % (ab,))
        self.assertEqual(r["requestsAtBackstop"], 1, "one document request on the wire past the backstop: the held fetch was not torn down (round 4: two): %r" % (r["requests"],))
        ld = r["landed"]
        self.assertGreaterEqual(ld.get("ms", -1), 0, "the held request was answered and the document loaded and painted on the kept src within the wait: %r" % (ld,))
        self.assertEqual((ld["src"], ld["dataSrc"], ld["sets"], ld["divFailed"], ld["bodyFailed"], ld["divLoading"], ld["bodyLoading"]), ("/waiting", "/waiting", 1, False, False, False, False), "landed: one src set for the page's life, no state: %r" % (ld,))
        self.assertTrue(ld["url"].endswith("/waiting") and ld["spinGone"] and ld["head"], "its document is the Waiting page, painted: %r" % (ld,))
        self.assertEqual((r["after"]["sets"], r["after"]["src"]), (1, "/waiting"), "and nothing promoted again: %r" % (r["after"],))
        self.assertEqual((len(r["requests"]), r["routeHeld"]), (1, 1), "one document request in all, the held one: %r" % (r["requests"],))
        self.assertEqual([x for x in r["rows"] if x["what"] == "pane-load-failed"], [{"what": "pane-load-failed", "pane": "waiting", "via": "backstop", "n": 1}],
                         "one row via the backstop: the 30 s uncommitted document is recorded (the hold keeps the src; the load that landed ended the episode): %r" % (r["rows"],))
        self.assertEqual([x for x in r["rows"] if x["what"] == "pane-load-unmarked"], [], "nothing was shown as served")
        self.assertEqual(r["errors"], [], "no page errors")


if __name__ == "__main__":
    unittest.main()
