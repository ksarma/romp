#!/usr/bin/env python3
"""A return from the background whose sockets reopen at once writes nothing to the Log; a real outage still does
(iOS item 4b, 2026-10-03).

The finding (PR 950's round 0, item 4b of its queue): every return to the app logged "Kernel connection lost" for the
chat and for the Feed, the Feed off screen on the phone, and left an unread digit on the Log control, although the sockets
came back at once. The shell's Log wrote the entry at each pane's up-to-down transition, and a return always makes one:
the shim's fast path puts a stale socket down before it redials, and the FIN a thawed page receives closes a socket the
OS dropped. That is a false interrupt. The entry now waits for the event that says the reconnect failed: a dial that closed
without ever opening, the pane's own (the shim's wsFail word) or the shell's (its link, which the panes wait on at a
return); a socket that reopens first takes the waiting entry with it, unwritten (kernel/kernel.py: _LANDING_ERRS_JS
`lost`, the shim's netFail, the shell socket's close in _LANDING_MOBILE_JS).

The lab: one hermetic kernel (test_ship_reship_served.kernel_env: a private state root with session hosts off, poisoned
manager port, no catalog or update fetch, a postal bus of its own) on a port from tests/lab_ports.py, no sessions. The
driver (tests/conn_lost_log_browser.mjs) opens the served shell as a phone (an iPhone descriptor at 390 x 844) or a desktop
window (1600 x 760), waits for every eager pane socket and the shell's own socket, reads the Log once (the boot's own
entries are seen from then on), then hides every document, closes the held sockets, waits 400 ms and shows them again, and
records every write to the Log (window.__rompNotify, wrapped as it is assigned), the Log's entries with their unread state,
the Log control's digit and red cue, and the panes' socket words to the shell. The sockets close at the suspend (the OS
dropped them while the page slept) or, in the `fin_after` legs, right after the return's handlers ran (the FIN a thawed page
receives). The regimes: healthy (every redial passes), kernel down (from the suspend every dial is refused at once), pane
dials refused (the shell's own dial passes, so the panes' own failed dials are the only failure), and hung (every dial
stays CONNECTING until the outage ends at 18 s; the shell's 15 s connect cut is the failure).

What each leg asserts. Healthy: the return put a pane socket down (the event the old rule wrote on) and every socket came
back, yet no connection-lost entry was written, the Log holds what it held, and the digit and the red cue are as before.
An outage: one entry per shown pane whose socket was down, written no earlier than the first failed dial, unread, the digit
counting them, and still unread after the sockets come back; in the hung leg nothing is written before the cut. Red at the
fork's main 591436b2e on every healthy leg (the transition wrote the entries) and on the hung leg's before-the-cut read and
the outage legs' written-at-a-failure check.

Engines: Chromium runs every leg (CI's served-pages job); Firefox and WebKit run the healthy phone and desktop legs, the
kernel-down phone leg and the pane-dials-refused leg, as optional legs that skip with "optional:" where the runner does
not declare the engine (ROMP_SERVED_TESTS_ENGINES). Skips loudly without the extension deps or a browser. CONN_LOG_OUT,
when set, receives every leg's driver record. Synthetic throughout: no real session data.
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
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes: an imported TestCase would be collected twice)

# Hermetic state before anything: this module loads no romp code in-process (the kernel is a subprocess under kernel_env's
# roots), and a later edit that adds a load must not write real state.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)

DRIVER = os.path.join(HERE, "conn_lost_log_browser.mjs")
OUT_DIR = os.environ.get("CONN_LOG_OUT", "")


def pane_labels():
    """kernel.py's _PANE_ORDER read as text, key to label: the six pane documents the shell serves iframes for, and the names
    the entries give them."""
    src = Path(os.path.join(ROOT, "kernel", "kernel.py")).read_text(encoding="utf-8")
    m = re.search(r"^_PANE_ORDER = \((.*?)\)\n", src, re.S | re.M)
    assert m, "kernel.py defines _PANE_ORDER"
    pairs = dict(re.findall(r'\("([a-z]+)", "([^"]+)"\)', m.group(1)))
    assert len(pairs) == 6 and {"chat", "feed"} <= set(pairs), pairs
    return pairs


PHONE_EAGER = ("chat", "feed")   # the phone loads the chat (its src ships) and the Feed (exempt from the lazy boot) at boot; every other pane at its first tap (stage 0)


def eager(shell):
    """The panes whose documents the shell loads at boot: all six on the desktop, the chat and the Feed on the phone."""
    return tuple(a for a in pane_labels() if shell != "phone" or a in PHONE_EAGER)


def unread(log):
    return [e for e in log["entries"] if not e["seen"]]


def digit(n):
    """What the Log control draws for n unread entries (_LANDING_ERRS_JS paint)."""
    return "!" if n <= 0 else ("+" if n > 9 else str(n))


class ConnLostLog(unittest.TestCase):
    """One lab kernel for every leg; each leg is one driver run in a fresh browser context."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.kernel, cls.lab, cls.legs = None, None, {}
        try:
            cls._boot()
        except BaseException:
            cls.tearDownClass()
            raise

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served legs need them")
        cls.lab = tempfile.mkdtemp(prefix="connlog-")
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's one build of the bundles, copied under its lock (tests/lab_dist.py)
        claude = os.path.join(cls.lab, "claude")
        os.makedirs(claude, exist_ok=True)
        cls.port, cls.token = lab_ports.reserve(cls.lab), "testtok-connlog"
        cls.env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"),
                                      stderr=subprocess.STDOUT, env=cls.env)
        why = lab_ports.wait_owned(cls.kernel, cls.env)
        if why:
            raise unittest.SkipTest("hermetic kernel never served /healthz here: " + why)

    @classmethod
    def tearDownClass(cls):
        if cls.lab and cls.legs and OUT_DIR:
            os.makedirs(OUT_DIR, exist_ok=True)
            Path(OUT_DIR, "conn-log-legs.json").write_text(json.dumps(cls.legs, indent=1, sort_keys=True))
        if cls.kernel:
            try:
                os.kill(cls.kernel.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            cls.kernel.wait()
        if cls.lab:
            lab_ports.release(cls.lab)
            shutil.rmtree(cls.lab, ignore_errors=True)

    # ---- the driver ----
    def _drive(self, engine, shell, regime, fin="suspend", outage_ms=0, reads_ms=()):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        name = "%s-%s-%s-fin-%s" % (engine, shell, regime, fin)
        self.assertTrue(eager(shell), "the eager set for the %s shell is not empty" % shell)
        cfg = {"engine": engine, "shell": shell, "regime": regime, "fin": fin, "outageMs": outage_ms, "readsMs": list(reads_ms),
               "url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token), "healthz": "http://127.0.0.1:%d/healthz" % self.port,
               "eagerApps": list(eager(shell)), "hiddenDwellMs": 400, "settleMs": 1500, "afterMs": 2000}
        path = os.path.join(self.lab, "cfg-%s.json" % name)
        Path(path).write_text(json.dumps(cfg))
        try:
            p = subprocess.run(["node", DRIVER], capture_output=True, text=True, timeout=180,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=path))
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
        type(self).legs[name] = r
        self.assertNotIn("died", r, "driver aborted: %r (kernel log tail: %s)" % (r.get("died"), Path(self.klog).read_text()[-800:]))
        self.assertEqual([x for x in r["installed"] if x.endswith(":MISSING")], [], name + ": every document reads the emulated visibility")
        self.assertTrue(r["upAfterReturn"], name + ": every eager pane and the shell's link said up after the return or the outage")
        boot = r["logAtBoot"]
        self.assertEqual(unread(boot), [], name + ": the Log was read before the suspend")
        self.assertEqual((boot["digit"], boot["has"]), ("!", False), name + ": the control shows nothing unread and no live drop before the suspend")
        downs = [w for w in r["ws"] if w["romp"] == "wsState" and w["state"] == "down" and w["t"] >= r["t"]["suspend"]]
        self.assertTrue(downs, name + ": the return put a pane socket down, the event the old rule wrote its entry on: %r" % r["ws"])
        return name, r

    def _expected(self, r, shell):
        """The entries an outage owes: one per eager pane the shell shows (its po-<key> class), by the pane's label."""
        labels, body = pane_labels(), r["bodyClass"].split()
        want = sorted("Kernel connection lost: %s pane (reconnecting)" % labels[a] for a in eager(shell) if "po-" + a in body)
        self.assertTrue(want, "a shown eager pane exists to owe an entry: %r" % body)
        return want

    def _conn(self, r):
        return [n for n in r["notify"] if n["kind"] == "conn" and n["t"] >= r["t"]["suspend"]]

    # ---- a healthy return: the sockets reopen at once, nothing is written ----
    def _healthy(self, engine, shell, fin):
        name, r = self._drive(engine, shell, "healthy", fin)
        self.assertLess(r["t"]["up"] - r["t"]["return"], 15000, name + ": the sockets came back at once, not after a cut")
        self.assertEqual(self._conn(r), [], name + ": a return whose sockets reopen at once writes no connection-lost entry")
        after = r["logAfter"]
        self.assertEqual(after["entries"], r["logAtBoot"]["entries"], name + ": the Log holds what it held before the suspend")
        self.assertEqual((after["digit"], after["has"]), ("!", False), name + ": no unread digit and no red cue after the return")

    # ---- an outage: the entry is written at the reconnect's failure, unread ----
    def _outage(self, engine, shell, regime, outage_ms, reads_ms):
        name, r = self._drive(engine, shell, regime, "suspend", outage_ms, reads_ms)
        t_s = r["t"]["suspend"]
        failed = [d for d in r["dials"] if d["t"] >= t_s and d.get("verdict") in ("refused", "hung-cut")]
        self.assertTrue(failed, name + ": the outage refused or cut a dial after the return: %r" % r["dials"])
        first_fail = min(d["t"] for d in failed)   # the arrival of the first dial that went on to fail: its failure (the page's close) comes after
        want = self._expected(r, shell)
        conn = self._conn(r)
        self.assertEqual(sorted(n["text"] for n in conn), want, name + ": one entry per shown pane whose socket was down")
        early = [n for n in conn if n["t"] < first_fail]
        self.assertEqual(early, [], name + ": every entry was written after a failing dial was made, none at the drop before it (at %d)" % first_fail)
        last = r["reads"][-1]["log"]
        got = sorted(e["text"] for e in unread(last) if e["kind"] == "conn")
        self.assertEqual(got, want, name + ": during the outage the entries are unread")
        self.assertEqual((last["digit"], last["has"]), (digit(len(unread(last))), True), name + ": the control counts them, red")
        after = r["logAfter"]
        self.assertEqual(sorted(e["text"] for e in unread(after) if e["kind"] == "conn"), want, name + ": still unread once the sockets are back")
        self.assertEqual([e["n"] for e in after["entries"] if e["kind"] == "conn"], [1] * len(want), name + ": one entry per pane for the one outage")
        self.assertEqual(after["digit"], digit(len(unread(after))), name + ": the digit still counts them")
        return name, r, first_fail

    def test_phone_healthy_return(self):
        self._healthy("chromium", "phone", "suspend")

    def test_phone_healthy_return_fin_after_the_return(self):
        self._healthy("chromium", "phone", "return")

    def test_desktop_healthy_return(self):
        self._healthy("chromium", "desktop", "suspend")

    def test_desktop_healthy_return_fin_after_the_return(self):
        self._healthy("chromium", "desktop", "return")

    def test_phone_kernel_down(self):
        self._outage("chromium", "phone", "refused", 5000, (1500, 4500))

    def test_desktop_kernel_down(self):
        self._outage("chromium", "desktop", "refused", 5000, (1500, 4500))

    def test_phone_pane_dials_refused_while_the_link_stands(self):
        name, r, _ = self._outage("chromium", "phone", "refused-panes", 5000, (1500, 4500))
        self.assertEqual([d["verdict"] for d in r["dials"] if d["app"] == "shell" and d["t"] >= r["t"]["suspend"]], ["passed"],
                         name + ": the shell's own dial passed, so the panes' own failed dials are what wrote the entries")

    def test_phone_hung_until_the_connect_cut(self):
        name, r, _ = self._outage("chromium", "phone", "hung", 18000, (5000, 17000))
        cut = [d for d in r["dials"] if d["t"] >= r["t"]["suspend"] and d.get("verdict") == "hung-cut"]
        self.assertTrue(cut and all(d["cutT"] - d["t"] >= 14000 for d in cut), name + ": the page cut its hung dial at the 15 s connect cut: %r" % cut)
        self.assertGreaterEqual(min(n["t"] for n in self._conn(r)) - r["t"]["return"], 14000, name + ": the entries were written at that cut, not at the drop")
        before = r["reads"][0]["log"]
        self.assertEqual([e for e in unread(before) if e["kind"] == "conn"], [], name + ": a dial still CONNECTING has not failed: nothing written before the cut")
        self.assertEqual(before["has"], True, name + ": the live red cue shows the drop meanwhile")

    def test_firefox_phone_healthy_return(self):
        self._healthy("firefox", "phone", "suspend")

    def test_firefox_desktop_healthy_return(self):
        self._healthy("firefox", "desktop", "suspend")

    def test_firefox_phone_kernel_down(self):
        self._outage("firefox", "phone", "refused", 5000, (1500, 4500))

    def test_firefox_phone_pane_dials_refused_while_the_link_stands(self):
        self._outage("firefox", "phone", "refused-panes", 5000, (1500, 4500))

    def test_webkit_phone_healthy_return(self):
        self._healthy("webkit", "phone", "suspend")

    def test_webkit_desktop_healthy_return(self):
        self._healthy("webkit", "desktop", "suspend")

    def test_webkit_phone_kernel_down(self):
        self._outage("webkit", "phone", "refused", 5000, (1500, 4500))

    def test_webkit_phone_pane_dials_refused_while_the_link_stands(self):
        self._outage("webkit", "phone", "refused-panes", 5000, (1500, 4500))


if __name__ == "__main__":
    unittest.main()
