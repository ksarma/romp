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
dials refused (the shell's own dial passes, so the panes' own failed dials are the only failure), hung (every dial
stays CONNECTING until the outage ends at 18 s; the shell's 15 s connect cut is the failure), and slow (the review of
item 4b, 2026-10-03: every handshake succeeds, but the driver holds the dials in one line, SLOW_MS each, the order
Chromium and Firefox keep on a real network; a routed socket is a mock in the page, so the engine's own line does not
apply here). In the `return-panes-first` leg the panes' sockets close before the shell's, so the panes redial while the
shell's link stands and the shell's own redial waits behind theirs.

What each leg asserts. Healthy: the return put a pane socket down (the event the old rule wrote on) and every socket came
back, yet no connection-lost entry was written, the Log holds what it held, and the digit and the red cue are as before.
An outage: one entry per shown pane whose socket was down, written no earlier than the first failed dial, unread, the digit
counting them, and still unread after the sockets come back; in the hung leg nothing is written before the cut. A slow
return: the page's own connect cut, a timer, closed a shown pane's dial while it waited in line and another socket of the
page stood (in the `return-panes-first` leg the shell's own redial too, while a pane's socket stood), every other dial
passed, and nothing was written: a close that cut made fails nothing while a socket of the page is open. Red at the fork's
main 591436b2e on every return leg above, in each engine it runs in: each healthy and slow leg on its no-entry check (the
transition wrote one entry per shown pane), each outage leg, the hung one included, on its written-after-a-failing-dial check
(the entries were written at the drop, before any dial had failed). The slow legs are red too at ed1c13e73, this branch's head before the
review's finding was fixed, on the same check: the cut of a pane's dial, or of the shell's, wrote the shown panes still
waiting in line.

The unload legs (review round 1 of item 4b, 2026-10-04) drive tests/conn_lost_reload_browser.mjs instead: real engine sockets
through a TCP proxy the driver runs on a second reserved port, since a routed socket is a mock no engine closes on unload. A
reload while the shell's return dial is CONNECTING (reload-return) or while the shown panes' boot dials are (reload-boot)
writes nothing. Firefox closes such dials after beforeunload and before pagehide and delivers their closes to the unloading
page: at d8a1df87e the old page then wrote one unread entry per shown pane, 3 on the desktop, through the shell's
window.__rompLinkFailed in reload-return and through the panes' wsFail words in reload-boot, and both Firefox legs are red there
on their no-entry check. Chromium and WebKit deliver no such close; their reload legs hold that a reload still writes nothing.
Each reload leg asserts that the old page's dials were CONNECTING when the reload began, and the Firefox legs that the old
page received the failure after its beforeunload. A navigation to a 204 fires beforeunload and leaves the page in place, and
an outage after it still writes one unread entry per shown pane: green at d8a1df87e, which has no latch, and red under a
latch that never clears. The paneonly legs take the panes down alone after the 204, while the shell's link stands. In
Chromium and WebKit the 204 closes no socket, so the latch it set stays set until the next frame on the shell's link clears
it (review round 1 of item 4b, call 1, 2026-10-04); those legs wait for such a frame after the 204's beforeunload, then hold
that the outage writes one unread entry per shown pane, with no dial of the shell's, no open of any socket and no pageshow
between the 204 and the outage's end to clear the latch instead. Red at 3e9c560f5, before the frame cleared it, on that check: the latch held every refusal of
the outage and the panes' opens dropped the waiting entries, so nothing was written. Firefox closes every socket at the 204,
the shell's redial about 2 s later clears the latch, and its paneonly leg writes an entry for every shown pane whose dial was
refused, green at 3e9c560f5 too. The reload legs are the other side of that clear: a frame on the link between an unload's
beforeunload and the closes Firefox delivers would clear the latch, and they hold that a reload still writes nothing. Two
Firefox legs execute that race, the risk call 1 accepted: the driver delivers one keepalive frame on the open link from a
beforeunload listener added after the page's own, in a reload during the boot dials and in one during a return's pane redials
(the shell's return dial passes and the shown panes' dials are held, so they connect beside the open link), and each such reload
writes one unread entry per shown pane, which the reloaded page shows. Red at 3e9c560f5, whose link frames clear nothing, on
their written check. They pin the residual as it executes: one going red means the race changed.

Engines: Chromium runs every leg but the two frame legs (CI's served-pages job); Firefox and WebKit run the healthy phone and
desktop legs, the kernel-down phone leg, the pane-dials-refused leg, the unload legs and the paneonly legs, and Firefox alone
runs the two frame legs (only Firefox delivers an unload's closes to the page), as optional legs that skip with
"optional:" where the runner does not declare the engine (ROMP_SERVED_TESTS_ENGINES). The slow legs run in Chromium alone:
their line is the driver's, so another engine would run the same page code against the same line. Skips loudly without the
extension deps or a browser.
CONN_LOG_OUT, when set, receives every leg's driver record. Synthetic throughout: no real session data.
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
RELOAD_DRIVER = os.path.join(HERE, "conn_lost_reload_browser.mjs")   # the unload legs' driver: real sockets through its own proxy
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


SLOW_MS = 5500   # the slow legs' handshake: the Feed, fourth of the panes in the desktop's line, opens 22 s after its dial, past the latest its connect cut can come (15 s and one 5 s watchdog tick)
PHONE_EAGER = ("chat", "feed")   # the phone loads the chat (its src ships) and the Feed (exempt from the lazy boot) at boot; every other pane at its first tap (stage 0)
HELD_AT_BOOT = ("chat", "feed", "timeline")   # the reload-boot legs hold the panes the desktop shows by default (the leg checks the body says so)


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
        cls.pport = lab_ports.reserve(cls.lab)   # the unload legs' proxy (tests/conn_lost_reload_browser.mjs listens on it)
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
    def _drive(self, engine, shell, regime, fin="suspend", outage_ms=0, reads_ms=(), handshake_ms=0, up_ms=0):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        name = "%s-%s-%s-fin-%s" % (engine, shell, regime, fin)
        self.assertTrue(eager(shell), "the eager set for the %s shell is not empty" % shell)
        cfg = {"engine": engine, "shell": shell, "regime": regime, "fin": fin, "outageMs": outage_ms, "readsMs": list(reads_ms),
               "url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token), "healthz": "http://127.0.0.1:%d/healthz" % self.port,
               "eagerApps": list(eager(shell)), "hiddenDwellMs": 400, "settleMs": 1500, "afterMs": 2000}
        if handshake_ms:
            cfg["handshakeMs"] = handshake_ms
        if up_ms:
            cfg["upTimeoutMs"] = up_ms
        cfg["resultPath"] = os.path.join(self.lab, "result-%s.json" % name)   # the driver's full record; its RESULT: line names it
        path = os.path.join(self.lab, "cfg-%s.json" % name)
        Path(path).write_text(json.dumps(cfg))
        try:
            p = subprocess.run(["node", DRIVER], capture_output=True, text=True, timeout=240,
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
        r = self._full_result(line, cfg["resultPath"], p)
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

    def _full_result(self, line, result_path, p):
        """The driver's record, from the file its RESULT: line names. The line stays short: the driver's stdout is
        non-blocking, so one write to a pipe delivers what the pipe has room for, which was 8 KiB on a loaded machine, and a
        24 KB record printed whole was cut there."""
        head = json.loads(line[len("RESULT:"):])
        self.assertEqual(head.get("resultPath"), result_path, "the driver named its result file: %r" % head)
        self.assertTrue(os.path.exists(result_path), "the driver wrote its result (%r; died: %r):\n%s" % (
            head.get("resultWriteError"), head.get("died"), (p.stdout[-1500:] + p.stderr[-1500:])))
        return json.loads(Path(result_path).read_text(encoding="utf-8"))

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

    # ---- a slow return: the handshakes open one at a time, every one succeeds, nothing is written ----
    def _slow(self, engine, shell, fin):
        """A return on a slow network (the review of item 4b, 2026-10-03). The driver keeps the line Chromium and Firefox keep
        (one WebSocket handshake to a host at a time, RFC 6455 section 4.1), each handshake taking SLOW_MS. On the desktop the
        panes a return dials together then wait in line behind each other, and the page's own 15 s connect cut, a timer, closes
        the dials still waiting, the Feed's among them (fourth in line, shown by default), although every handshake was
        succeeding. A close that cut made fails nothing while another socket of the page is open, so nothing is written."""
        name, r = self._drive(engine, shell, "slow", fin, handshake_ms=SLOW_MS, up_ms=90000)
        after = [d for d in r["dials"] if d["t"] >= r["t"]["suspend"]]
        self.assertTrue(after, name + ": the return dialed")
        self.assertEqual([d for d in after if d.get("verdict") not in ("passed", "slow-cut")], [],
                         name + ": every dial either passed after its turn in line or was cut by the page while it waited: %r" % after)
        body = r["bodyClass"].split()
        opened = sorted(d["openT"] for d in after if d["verdict"] == "passed")
        self.assertTrue(opened, name + ": the dials in line opened: %r" % after)
        stood = [d for d in after if d["verdict"] == "slow-cut" and d["app"] != "shell" and "po-" + d["app"] in body and d["cutT"] > opened[0]]
        self.assertTrue(stood, name + ": the page's connect cut closed a SHOWN pane's dial while it waited in line and another socket of "
                        "the page stood, the close the old rule wrote an entry for: %r" % after)
        self.assertEqual(self._conn(r), [], name + ": a slow return whose handshakes all succeed writes no connection-lost entry")
        log = r["logAfter"]
        self.assertEqual(log["entries"], r["logAtBoot"]["entries"], name + ": the Log holds what it held before the suspend")
        self.assertEqual((log["digit"], log["has"]), ("!", False), name + ": no unread digit and no red cue once the sockets are back")
        return name, r, after, opened

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

    def test_desktop_slow_return(self):
        name, r, after, opened = self._slow("chromium", "desktop", "suspend")
        shell = [d["openT"] for d in after if d["app"] == "shell" and d["verdict"] == "passed"]
        self.assertTrue(shell, name + ": the shell's own dial passed first: %r" % after)
        self.assertTrue([d for d in after if d["verdict"] == "slow-cut" and d["app"] != "shell" and d["cutT"] > shell[0]],
                        name + ": a pane dial was cut while the shell's link stood")

    def test_desktop_slow_return_fin_on_the_panes_first(self):
        name, r, after, opened = self._slow("chromium", "desktop", "return-panes-first")
        panes = [d["openT"] for d in after if d["app"] != "shell" and d["verdict"] == "passed"]
        cut = [d for d in after if d["app"] == "shell" and d["verdict"] == "slow-cut"]
        self.assertTrue(cut and panes and cut[0]["cutT"] > min(panes),
                        name + ": the shell's own redial waited behind the panes' and its connect cut closed it while a pane's socket "
                        "stood, so its link's failure fails nothing: %r" % after)

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

    # ---- the page's own unload, through real sockets (review round 1 of item 4b, 2026-10-04) ----
    def _drive_real(self, engine, scenario, **extra):
        """One run of tests/conn_lost_reload_browser.mjs on the desktop shell: real engine sockets through the driver's own
        proxy on the reserved port, in front of the lab kernel."""
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        name = "%s-desktop-%s" % (engine, scenario) + ("-frame" if extra.get("frameAtUnload") else "")
        cfg = {"engine": engine, "shell": "desktop", "scenario": scenario, "token": self.token, "kernelPort": self.port,
               "proxyPort": self.pport, "healthz": "http://127.0.0.1:%d/healthz" % self.port, "eagerApps": list(eager("desktop")),
               "hiddenDwellMs": 400, "settleMs": 1500, "afterMs": 2000}
        cfg.update(extra)
        cfg["resultPath"] = os.path.join(self.lab, "result-%s.json" % name)   # the driver's full record; its RESULT: line names it
        path = os.path.join(self.lab, "cfg-%s.json" % name)
        Path(path).write_text(json.dumps(cfg))
        try:
            p = subprocess.run(["node", RELOAD_DRIVER], capture_output=True, text=True, timeout=240,
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
        r = self._full_result(line, cfg["resultPath"], p)
        type(self).legs[name] = r
        self.assertNotIn("died", r, "driver aborted: %r (kernel log tail: %s)" % (r.get("died"), Path(self.klog).read_text()[-800:]))
        self.assertTrue(r["upAfter"], name + ": every eager pane and the shell's link said up at the end (kernel log tail: %s)"
                        % Path(self.klog).read_text()[-1500:])
        return name, r

    def _reload(self, engine, scenario):
        """A reload while a dial of the page is still CONNECTING writes nothing. Firefox closes the old page's never-opened
        dials after beforeunload and before pagehide and delivers their close events while that page still runs: in
        reload-return the shell's return dial (window.__rompLinkFailed), in reload-boot every boot dial (each pane's down
        word and its wsFail word). Before the leaving latch each such close was read as a failed reconnect, and the old page
        wrote one unread entry per shown pane, which the reloaded page showed. Chromium and WebKit deliver no close events to
        an unloading page; their legs hold that the reload still writes nothing there."""
        name, r = self._drive_real(engine, scenario, **({"holdApps": list(HELD_AT_BOOT)} if scenario == "reload-boot" else {}))
        rec, old = r["rec"], r["oldGen"]
        self.assertNotEqual(r["newGen"], old, name + ": the page reloaded")
        before_unload = [e["t"] for e in rec["ev"] if e["gen"] == old and e["ev"] == "beforeunload"]
        self.assertTrue(before_unload, name + ": the old page's beforeunload fired, the event the latch is set on")
        # the dials in flight at the reload, read from the old page's own sockets (a dial Firefox or Chromium keeps waiting in
        # its handshake line, or Firefox delays after a failure, never reaches the proxy, and is CONNECTING all the same)
        held = ["shell"] if scenario == "reload-return" else list(HELD_AT_BOOT)
        if scenario == "reload-boot":
            self.assertEqual(sorted(held), sorted(a for a in eager("desktop") if "po-" + a in r["bodyClass"].split()),
                             name + ": the dials held at the boot are the shown panes'")
        for app in held:
            last = [x["ev"] for x in rec["sock"] if x["gen"] == old and x["app"] == app and x["t"] < r["t"]["reload"]][-1:]
            self.assertEqual(last, ["dial"], name + ": the old page's %s dial was CONNECTING when the reload began" % app)
        road = "linkFailed" if scenario == "reload-return" else "wsFail"
        during = [e for e in rec["ev"] if e["gen"] == old and e["ev"] == road and e["t"] >= before_unload[0]]
        if engine == "firefox":
            self.assertTrue(during, name + ": the old page received its never-opened dials' failure (%s) after its beforeunload, "
                            "the road the leg is about: %r" % (road, rec["ev"]))
        self.assertEqual([n for n in rec["notify"] if n["kind"] == "conn"], [],
                         name + ": no connection-lost entry was written, by the unloading page or by the reloaded one")
        self.assertEqual([e for e in r["logAfter"]["entries"] if e["kind"] == "conn"], [],
                         name + ": the reloaded page's Log holds no connection-lost entry")
        return name, r, during

    def test_firefox_desktop_reload_during_the_returns_redial(self):
        self._reload("firefox", "reload-return")

    def test_firefox_desktop_reload_during_the_boot_dials(self):
        self._reload("firefox", "reload-boot")

    def test_desktop_reload_during_the_returns_redial(self):
        self._reload("chromium", "reload-return")

    def test_desktop_reload_during_the_boot_dials(self):
        self._reload("chromium", "reload-boot")

    def test_webkit_desktop_reload_during_the_returns_redial(self):
        self._reload("webkit", "reload-return")

    def test_webkit_desktop_reload_during_the_boot_dials(self):
        self._reload("webkit", "reload-boot")

    def _reload_frame(self, scenario):
        """The race call 1 accepted, executed in Firefox (review round 1 of item 4b, 2026-10-04): a frame on the shell's link
        between an unload's beforeunload and the closes Firefox delivers clears the leaving latch, and that reload writes an
        entry for each shown pane whose dial the unload closed. The driver delivers one keepalive frame on the OPEN shell
        socket from a beforeunload listener added after the page's own (cfg.frameAtUnload). Exposed is any reload while a
        pane's dial connects beside the open link: the boot dials (reload-boot), and a return's pane redials, which wait for
        the link and dial once it is up (reload-return-panes: the shell's return dial passes, the shown panes' are held). The
        shell's own return dial is not exposed (reload-return: the link is down, so no frame can come). These legs pin the
        residual as it executes; one going red means the race changed, and the body's residual with it. Firefox alone:
        Chromium and WebKit deliver no close to an unloading page, so there is nothing for the frame to let through."""
        name, r = self._drive_real("firefox", scenario, holdApps=list(HELD_AT_BOOT), frameAtUnload=True)
        rec, old = r["rec"], r["oldGen"]
        self.assertNotEqual(r["newGen"], old, name + ": the page reloaded")
        self.assertEqual(sorted(HELD_AT_BOOT), sorted(a for a in eager("desktop") if "po-" + a in r["bodyClass"].split()),
                         name + ": the dials held are the shown panes'")
        before_unload = [e["t"] for e in rec["ev"] if e["gen"] == old and e["ev"] == "beforeunload"]
        self.assertTrue(before_unload, name + ": the old page's beforeunload fired, the event the latch is set on")
        self.assertEqual((r["atReload"]["link"], r["atReload"]["shellState"]), (True, 1),
                         name + ": at the reload the link read up and its socket was OPEN: %r" % r["atReload"])
        for app in HELD_AT_BOOT:
            last = [x["ev"] for x in rec["sock"] if x["gen"] == old and x["app"] == app and x["t"] < r["t"]["reload"]][-1:]
            self.assertEqual(last, ["dial"], name + ": the old page's %s dial was CONNECTING when the reload began" % app)
        shell = [x["ev"] for x in rec["sock"] if x["gen"] == old and x["app"] == "shell" and x["top"] and x["t"] < r["t"]["reload"]]
        self.assertEqual(shell[-1:], ["open"], name + ": the shell's last socket event before the reload was its open: %r" % shell)
        fired = [e["fired"] for e in rec["ev"] if e["gen"] == old and e["ev"] == "frameAtUnload"]
        self.assertEqual(fired, [True], name + ": one frame was delivered on the open link inside the unload's beforeunload")
        failed = sorted({e["app"] for e in rec["ev"] if e["gen"] == old and e["ev"] == "wsFail" and e["t"] >= before_unload[0]})
        self.assertEqual([a for a in sorted(HELD_AT_BOOT) if a not in failed], [],
                         name + ": the unload's closes of the shown panes' dials reached the old page as failure words: %r" % failed)
        labels = pane_labels()
        want = sorted("Kernel connection lost: %s pane (reconnecting)" % labels[a] for a in HELD_AT_BOOT)
        self.assertEqual(sorted(n["text"] for n in rec["notify"] if n["kind"] == "conn" and n["gen"] == old), want,
                         name + ": the frame cleared the latch, so the unloading page wrote one entry per shown pane")
        self.assertEqual([n for n in rec["notify"] if n["kind"] == "conn" and n["gen"] != old], [],
                         name + ": the reloaded page wrote none of its own")
        self.assertEqual(sorted(e["text"] for e in r["logAfter"]["entries"] if e["kind"] == "conn" and not e["seen"]), want,
                         name + ": the reloaded page's Log shows them unread")
        return name, r

    def test_firefox_desktop_reload_during_the_boot_dials_with_a_frame_in_the_unloads_window(self):
        self._reload_frame("reload-boot")

    def test_firefox_desktop_reload_during_the_returns_pane_redials_with_a_frame_in_the_unloads_window(self):
        self._reload_frame("reload-return-panes")

    def _nav204(self, engine, outage_ms=5000):
        """A navigation that fires beforeunload and does not unload (the top document sent to a 204; a download is the
        other) sets the leaving latch, and the latch clears at the page's next real event, so a later outage is still
        written. Firefox also closes every socket of the page at such a navigation, and they redial; Chromium closes none.
        A latch that never cleared would leave the Log silent for every outage after it, for the page's life."""
        name, r = self._drive_real(engine, "nav204-outage", outageMs=outage_ms, readsMs=[outage_ms - 500])
        rec, gen = r["rec"], r["oldGen"]
        t_nav, t_out = r["t"]["nav"], r["t"]["outage"]
        self.assertEqual(r["genAfterNav"], gen, name + ": the 204 left the page in place")
        self.assertTrue([e for e in rec["ev"] if e["gen"] == gen and e["ev"] == "beforeunload" and t_nav <= e["t"] < t_out],
                        name + ": the navigation fired beforeunload, so the latch was set: %r" % rec["ev"])
        self.assertEqual([e for e in rec["ev"] if e["ev"] == "pagehide"], [], name + ": the page never unloaded")
        self.assertEqual([n for n in rec["notify"] if n["kind"] == "conn" and n["t"] < t_out], [],
                         name + ": nothing failed before the outage")
        want = self._expected({"bodyClass": r["bodyClass"]}, "desktop")
        self.assertEqual(sorted(n["text"] for n in rec["notify"] if n["kind"] == "conn" and n["t"] >= t_out), want,
                         name + ": the outage after the 204 wrote one entry per shown pane")
        last = r["reads"][-1]["log"]
        self.assertEqual(sorted(e["text"] for e in last["entries"] if e["kind"] == "conn" and not e["seen"]), want,
                         name + ": during the outage the entries are unread")
        return name, r

    def test_firefox_desktop_a_204_then_an_outage_is_written(self):
        # Firefox delays a dial after a failed one (seconds, growing), so within a 5 s outage only the first pane's redial
        # reached the kernel; 18 s takes every dial past its refusal or its 15 s cut
        self._nav204("firefox", 18000)

    def test_webkit_desktop_a_204_then_an_outage_is_written(self):
        self._nav204("webkit")

    def test_desktop_a_204_then_an_outage_is_written(self):
        self._nav204("chromium")

    def _nav204_paneonly(self, engine, outage_ms=10000):
        """After a navigation that fires beforeunload and does not unload, an outage of the panes alone, while the shell's link
        stands: every pane's socket dropped, every pane's dial refused, the shell's socket never touched. In Chromium and
        WebKit the 204 closes nothing, so the leaving latch it set stays set until the next frame on the shell's link (review
        round 1 of item 4b, call 1, 2026-10-04). Their legs wait for that frame after the 204's beforeunload, and no other event
        that clears the latch happens from the 204 to the outage's end (no dial of the shell's, no open of any socket, no
        pageshow), so the frame is what lets the outage write one unread entry per shown pane. At 3e9c560f5, before the frame cleared the latch,
        the latch held every refusal of the outage and the panes' opens at its end dropped the waiting entries: nothing was
        written, during the outage or after it, and both legs are red on their written check. Firefox closes every socket of the
        page at the 204, the shell's redial clears the latch, and the outage writes an entry for every shown pane whose dial was
        refused. Firefox holds a host's handshakes in one line and delays a dial after a failed one, so in 10 s only two or
        three dials reach the kernel; its leg drops and refuses the shown panes alone, so every dial that reaches the kernel is
        one that owes an entry. It waits for no frame, and is green at 3e9c560f5 too."""
        if engine == "firefox":
            extra = {"outageApps": list(HELD_AT_BOOT)}
        else:
            extra = {"frameAfterNav": True}
        name, r = self._drive_real(engine, "nav204-paneonly", outageMs=outage_ms, readsMs=[3000, outage_ms - 500], **extra)
        rec, gen = r["rec"], r["oldGen"]
        t_nav, t_out, t_end = r["t"]["nav"], r["t"]["outage"], r["t"]["outageEnd"]
        self.assertEqual(r["genAfterNav"], gen, name + ": the 204 left the page in place")
        before_unload = [e["t"] for e in rec["ev"] if e["gen"] == gen and e["ev"] == "beforeunload" and t_nav <= e["t"] < t_out]
        self.assertTrue(before_unload, name + ": the navigation fired beforeunload, so the latch was set: %r" % rec["ev"])
        self.assertEqual([e for e in rec["ev"] if e["ev"] in ("pagehide", "pageshow") and e["t"] >= t_nav], [],
                         name + ": the page never unloaded and no pageshow fired, which would clear the latch")
        shell = [x for x in rec["sock"] if x["app"] == "shell" and x["top"] and t_out <= x["t"] <= t_end]
        self.assertEqual(shell, [], name + ": the shell's socket neither closed nor redialed during the outage (its redial "
                         "would clear the latch)")
        self.assertEqual([x["link"] for x in r["reads"]], [True] * len(r["reads"]), name + ": the shell's link stood throughout")
        body = r["bodyClass"].split()
        shown = sorted(a for a in eager("desktop") if "po-" + a in body)
        # a refusal is the proxy's during the outage alone, so every refused dial's word counts, one landing just after its end too
        failed = sorted({e["app"] for e in rec["ev"] if e["ev"] == "wsFail" and not e.get("cut") and e["t"] >= t_out})
        labels = pane_labels()
        conn = [n for n in rec["notify"] if n["kind"] == "conn" and n["t"] >= t_nav]
        if engine == "firefox":
            self.assertEqual(shown, sorted(HELD_AT_BOOT), name + ": the panes the outage took down are the shown panes")
            want = sorted("Kernel connection lost: %s pane (reconnecting)" % labels[a] for a in failed if a in shown)
            self.assertTrue(want, name + ": a shown pane's dial was refused during the outage: %r" % failed)
            self.assertEqual(sorted(n["text"] for n in conn), want,
                             name + ": the 204's closes and redials cleared the latch, so every shown pane whose dial was refused was written")
            return name, r
        # the event under test: a frame on the shell's link after the 204's beforeunload, before the outage
        frames = [x["t"] for x in rec["frame"] if x["gen"] == gen and x["app"] == "shell" and before_unload[0] < x["t"] < t_out]
        self.assertTrue(frames, name + ": a frame reached the shell's link after the 204's beforeunload and before the outage, "
                        "the event that clears the latch: %r" % rec["frame"])
        # and no other event that clears it from the 204 to the outage's end: no dial of the shell's, no open of any socket (in
        # Chromium and WebKit the 204 closes none of them; the panes' own redials during the outage are refused), no pageshow
        cleared = [x for x in rec["sock"] if t_nav <= x["t"] < t_end and (x["ev"] == "open" or (x["ev"] == "dial" and x["app"] == "shell"))]
        self.assertEqual(cleared, [], name + ": nothing else cleared the latch: no dial of the shell's and no open of any socket "
                         "from the 204 to the outage's end")
        self.assertEqual(failed, sorted(eager("desktop")), name + ": every pane's dial was refused and posted its failure word "
                         "(cut false) during the outage")
        want = sorted("Kernel connection lost: %s pane (reconnecting)" % labels[a] for a in shown)
        self.assertTrue(want, name + ": a shown pane exists to owe an entry: %r" % body)
        self.assertEqual(sorted(n["text"] for n in conn), want,
                         name + ": the frame cleared the latch the 204 set, so the outage wrote one entry per shown pane")
        self.assertEqual([n for n in conn if n["t"] < t_out], [], name + ": nothing was written before the outage")
        last = r["reads"][-1]["log"]
        self.assertEqual(sorted(e["text"] for e in last["entries"] if e["kind"] == "conn" and not e["seen"]), want,
                         name + ": during the outage the entries are unread")
        after = r["logAfter"]
        self.assertEqual(sorted(e["text"] for e in after["entries"] if e["kind"] == "conn" and not e["seen"]), want,
                         name + ": still unread once the sockets are back")
        self.assertEqual([e["n"] for e in after["entries"] if e["kind"] == "conn"], [1] * len(want),
                         name + ": one entry per pane for the one outage")
        return name, r

    def test_desktop_a_204_then_a_pane_only_outage_is_written(self):
        self._nav204_paneonly("chromium")

    def test_webkit_desktop_a_204_then_a_pane_only_outage_is_written(self):
        self._nav204_paneonly("webkit")

    def test_firefox_desktop_a_204_then_a_pane_only_outage_is_written(self):
        self._nav204_paneonly("firefox")


if __name__ == "__main__":
    unittest.main()
