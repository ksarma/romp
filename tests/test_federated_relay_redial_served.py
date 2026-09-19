"""A federated page's relay REDIAL declares the pair its conn's bases hold, and nothing else (2026-09-19). Two hermetic
kernels on one box: a hub that owns no session and a checked-in TESTHOST that owns two ("api", "worker"). The hub's
Waiting-on-you page dials TESTHOST's relay socket and receives its full feed frame and the caps frame that answers the
page's ready; the driver then closes that socket from the page (its hook keeps the real socket it wrapped), federation.ts's
onclose retry redials 2 s later carrying reconnect=1 (the caps frame latched readyAcked), and the redial's caps term is
read against the frames the FIRST socket received.

The expectation is derived from the drive (tests/test_federated_dial_terms_served.py expected_relay_caps), so this lab
passes with either landing order of the client change and the kernel's generation stamp: a first full carrying gen means
the redial declares held:feed:<gen>.<rev>, the frames after it are a composed feedDelta and no {type:"feed"}, and the
remote counts one adopt and no undeclared eviction; a full carrying none (every kernel in this repo today) means
caps=feedDelta alone on the redial and a whole {type:"feed"} frame after it, today's counted full, which is what this lab
records at its base: until the kernel stamps its frames every remote redial stays undeclared. The derivation fails on an
empty drive (a first socket that recorded no frames). The hub's client-diag is read for the page's federation rows (the
positive control: the close and the second open, so the negatives below are over a live read) and for the absence of
feedDelta-nobase and feedDelta-stale rows (the redial's first frame seeded the base, nothing was refused).

This lab boots subprocess kernels and drives Chromium; it loads no romp code in-process, so it carries no in-process
state-isolation preamble and is not scanned by tests/test_state_isolation_order.py (as tests/test_federated_feed_delta_served.py,
whose shape it follows and whose kernel boot it reuses). Synthetic only: placeholder uuids, hostname TESTHOST, the
notes-api demo's session names.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from urllib.parse import parse_qs, urlsplit

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_federated_dial_terms_served as _dial   # noqa: E402  the two-kernel boot and the drive-derived caps expectation

SID_R0 = "11111111-2222-4333-8444-000000000701"   # "api" on TESTHOST
SID_R1 = "11111111-2222-4333-8444-000000000702"   # "worker" on TESTHOST
HOST = "TESTHOST"
WID = "hublab"
APP = "waiting"


def _state_root(lab, name):
    return os.path.join(lab, name, "xdg", "romp")


# The Chromium driver: hook every socket the page dials (window.__dials), keep the real socket (window.__socks) and record
# every frame a relay socket receives by socket index, type, slot and stamp fields (window.__frames: no content); open the
# hub's Waiting page; wait for the relay socket's full and caps frames; close the relay socket from the page; wait for the
# redial and for the first feed frame on it; report. The kernel-side observables are read from Python.
DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(cfg.launch || {}); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const context = await browser.newContext({ viewport: { width: 1200, height: 700 } });
const out = { dials: [], frames: [], firstIdx: null, secondIdx: null, died: null };
const hook = () => {
  window.__dials = []; window.__frames = []; window.__socks = []; const W = window.WebSocket;
  window.WebSocket = function (url, protos) {
    const u = String(url); const idx = window.__dials.length; window.__dials.push(u);
    const w = protos === undefined ? new W(u) : new W(u, protos);
    window.__socks.push(w);
    if (u.indexOf("/remote/") !== -1) {
      w.addEventListener("message", (ev) => {
        try {
          const m = JSON.parse(ev.data);
          if (m && m.type !== "ka") {
            const f = { sock: idx, t: String(m.type), slot: m.slot ? String(m.slot) : "" };
            for (const k of ["gen", "newGen", "base", "rev", "through"]) if (typeof m[k] === "number" || (typeof m[k] === "string" && (k === "gen" || k === "newGen"))) f[k] = m[k];   // the revs as numbers, the gens as the kernel's strings; no content
            window.__frames.push(f);
          }
        } catch (e) {}
      });
    }
    return w;
  };
  window.WebSocket.prototype = W.prototype; window.WebSocket.CONNECTING = 0; window.WebSocket.OPEN = 1; window.WebSocket.CLOSING = 2; window.WebSocket.CLOSED = 3;
};
const page = await context.newPage();
page.on("pageerror", () => {});
const relayIdx = () => page.evaluate(() => window.__dials.map((u, i) => [u, i]).filter(([u]) => u.indexOf("/remote/TESTHOST/ws") !== -1).map(([, i]) => i));
const snap = async () => Object.assign(out, await page.evaluate(() => ({ dials: (window.__dials || []).slice(), frames: (window.__frames || []).slice() })));
try {
  await page.addInitScript(hook);
  await page.goto(cfg.url);
  await page.waitForFunction(() => (window.__dials || []).some((u) => u.indexOf("/remote/TESTHOST/ws") !== -1), null, { timeout: 30000 });
  // the remote's full frame on the relay socket, and its caps frame (the ready ack that arms the redial gate)
  await page.waitForFunction(() => (window.__frames || []).some((f) => f.t === "feed") && (window.__frames || []).some((f) => f.t === "caps"), null, { timeout: 30000 });
  out.firstIdx = (await relayIdx())[0];
  // the page closes its relay socket: federation.ts's onclose retry redials 2 s later
  await page.evaluate((i) => { window.__socks[i].close(); }, out.firstIdx);
  await page.waitForFunction(() => (window.__dials || []).filter((u) => u.indexOf("/remote/TESTHOST/ws") !== -1).length >= 2, null, { timeout: 20000 });
  out.secondIdx = (await relayIdx())[1];
  // the first feed frame the redialed socket receives: whole, or a composed delta, whichever the remote serves
  await page.waitForFunction((i) => (window.__frames || []).some((f) => f.sock === i && (f.t === "feed" || f.t === "feedDelta")), out.secondIdx, { timeout: 20000 });
  await page.waitForTimeout(1500);   // let the page's rows about the redial land on the hub
  await snap();
} catch (e) {
  out.died = String(e).slice(0, 400);
  try { await snap(); } catch (e2) {}
}
console.log("RESULT:" + JSON.stringify(out));
await browser.close();
"""


def _is_page_federation_row(r):
    """A row the hub's page posted through federation.ts diag() about TESTHOST's relay socket (surface federation, what
    hostconn, data.host TESTHOST)."""
    return r.get("surface") == "federation" and r.get("what") == "hostconn" and (r.get("data") or {}).get("host") == HOST


class FederatedRelayRedial(unittest.TestCase):
    """Two kernels (a hub and a checked-in TESTHOST), one page, one driver run in setUpClass; each method asserts one observable."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.procs = []
        try:
            cls._boot()
        except BaseException:          # a skip OR a failure: never leave a kernel or a lab behind
            cls.tearDownClass()
            raise

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here), the served lab needs them")
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            raise unittest.SkipTest("no playwright browser on this box, the served lab needs one (CI installs none)")
        cls.lab = tempfile.mkdtemp(prefix="federated-relay-redial-")
        lab_dist.copy_dist(os.path.join(cls.lab, "dist"))   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        cls.rport, cls.rtoken = _dial._free_port(), "testtok-remote-rr"
        cls.hport, cls.htoken = _dial._free_port(), "testtok-hub-rr"
        rp, cls.rlog = _dial._kernel(cls.lab, "testhost", cls.rport, cls.rtoken, [(SID_R0, "api", 1), (SID_R1, "worker", 2)])
        cls.procs.append(rp)
        hp, cls.hlog = _dial._kernel(cls.lab, "hub", cls.hport, cls.htoken, [])
        cls.procs.append(hp)
        _dial.checkin(cls.hport, cls.htoken, cls.rport, cls.rtoken)
        cls.result, cls.driver_error = None, None
        cls._drive()
        cls.remote_wire = cls._remote_wire_memos()
        cls.hub_diag_rows = cls._read_hub_diag_rows()

    @classmethod
    def _drive(cls):
        cfg = os.path.join(cls.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump({"url": "http://127.0.0.1:%d/%s?wid=%s&token=%s" % (cls.hport, APP, WID, cls.htoken)}, f)
        driver = os.path.join(cls.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        try:
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=300,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        except subprocess.TimeoutExpired as e:
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            cls.driver_error = "driver timed out; partial output:\n%s" % so
            return
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box, the served leg needs one (CI installs none)")
        if p.returncode != 0:
            cls.driver_error = "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:]
            return
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        if line is None:
            cls.driver_error = "driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:]
            return
        cls.result = json.loads(line[len("RESULT:"):])

    @classmethod
    def _remote_wire_memos(cls):
        """The remote's memos.wire counters (/perf), read once after the driver."""
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/perf?token=%s" % (cls.rport, cls.rtoken), timeout=5) as r:
                perf = json.loads(r.read().decode())
            return ((perf.get("memos") or {}).get("wire")) or {}
        except Exception as e:
            return {"error": str(e)}

    @classmethod
    def _read_hub_diag_rows(cls):
        """Every row of the HUB's client-diag.jsonl, polled until it carries a federation hostconn row for TESTHOST whose
        event is the close the driver caused (the row the redial's negatives rest on); whatever was read on the timeout."""
        path = os.path.join(_state_root(cls.lab, "hub"), "client-diag.jsonl")
        rows = []
        for _ in range(20):
            rows = []
            try:
                with open(path) as fh:
                    for ln in fh:
                        try:
                            rows.append(json.loads(ln))
                        except ValueError:
                            continue
            except OSError:
                rows = []
            if any(_is_page_federation_row(r) and (r.get("data") or {}).get("ev") == "close" for r in rows):
                break
            time.sleep(0.3)
        return rows

    @classmethod
    def tearDownClass(cls):
        for p in getattr(cls, "procs", []):
            try:
                p.kill(); p.wait()
            except Exception:
                pass
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    # ---- the readers, each guarded so a derived expectation never rests on nothing ----
    def _driver_ran(self):
        if getattr(type(self), "driver_error", None):
            self.fail(type(self).driver_error)
        if getattr(type(self), "result", None) is None:
            raise unittest.SkipTest("the driver produced no result")
        if self.result.get("died"):
            self.fail("the driver died: %s" % self.result["died"])

    def _relay(self):
        """The two relay dials, [(index, host, url)], first then redial; guarded two, both to TESTHOST."""
        self._driver_ran()
        checked = _dial.relay_dials(self.result["dials"])
        self.assertEqual([h for _i, h, _u in checked], [HOST, HOST], "the page dialed TESTHOST's relay twice, the redial after the close: %r" % (self.result["dials"],))
        return checked

    def _frames_of(self, idx):
        """The frames the relay socket at dial index `idx` recorded (type, slot, stamp fields); guarded non-empty."""
        frames = [f for f in self.result.get("frames") or [] if f.get("sock") == idx]
        self.assertTrue(frames, "the relay socket at dial %d recorded frames: %r" % (idx, self.result.get("frames")))
        return frames

    def _first_pair(self):
        """The pair the first socket's frames left the conn (held_pair), after asserting the drive: a feed full arrived on it."""
        first, _redial = self._relay()
        frames = self._frames_of(first[0])
        self.assertIn("feed", [f["t"] for f in frames], "the first relay socket received the remote's full frame: %r" % (frames,))
        return _dial.held_pair(frames, "feed")

    # ---- the assertions ----
    def test_the_page_redialed_the_relay_it_closed_with_reconnect(self):
        first, redial = self._relay()
        self.assertLess(first[0], redial[0], "the redial came after the first dial")
        qs = parse_qs(urlsplit(redial[2]).query)
        self.assertEqual(qs.get("reconnect"), ["1"], "the remote's caps frame latched readyAcked before the close, so the redial states reconnect=1: %r" % (redial[2],))
        self.assertEqual(qs.get("app"), [APP])

    def test_the_redial_declares_the_pair_the_first_sockets_frames_left_and_nothing_else(self):
        # derived from the drive: the first socket's frames decide the redial's caps term, by the client's own rule
        checked = _dial.assert_relay_dials(self, APP, self.result["dials"], self.result.get("frames"))
        self.assertEqual(len(checked), 2)
        pair = self._first_pair()
        redial_caps = (parse_qs(urlsplit(checked[1][2]).query).get("caps") or [""])[0]
        if pair is None:
            self.assertEqual(redial_caps, "feedDelta", "the first full carried no gen (this checkout's kernel): the redial is undeclared, the decoder word alone")
        else:
            self.assertEqual(redial_caps, "feedDelta,held:feed:%s.%d" % pair, "the first full carried gen: the redial declares the pair the stream left")

    def test_the_frames_after_the_redial_match_the_declaration(self):
        pair = self._first_pair()
        _first, redial = self._relay()
        kinds = [(f["t"], f.get("base"), f.get("through")) for f in self._frames_of(redial[0])]
        types = [k[0] for k in kinds]
        if pair is None:
            self.assertIn("feed", types, "an undeclared redial is served the whole frame, today's counted full: %r" % (kinds,))
        else:
            self.assertNotIn("feed", types, "a declared redial is composed, never served whole: %r" % (kinds,))
            composed = [k for k in kinds if k[0] == "feedDelta" and k[2] is not None]
            self.assertEqual(len(composed), 1, "one composed feedDelta: %r" % (kinds,))
            self.assertEqual(composed[0][1], pair[1], "stamped base r, the declared rev")

    def test_the_remote_counts_the_redial_as_the_declaration_says(self):
        pair = self._first_pair()
        wire = self.remote_wire
        self.assertIn("feed_slot_split", wire, "the remote's /perf memos.wire counters were read (the positive control): %r" % (wire,))
        self.assertEqual(wire["feed_slot_split"], 0, "both dials announced the decoder word: no slot-path re-encode")
        adopt = wire.get("resume.feed.adopt") or 0
        if pair is None:
            self.assertEqual(adopt, 0, "no declaration, no adopt: the redial was served a whole frame")
        else:
            self.assertEqual(adopt, 1, "one adopt for the one declared redial: %r" % (wire,))
            self.assertEqual(wire.get("stash.evict.undeclared") or 0, 0, "nothing evicted as undeclared: %r" % (wire,))

    def test_the_hub_files_the_close_and_the_second_open_and_no_nobase_or_stale_row(self):
        self._driver_ran()
        control = [(r.get("data") or {}).get("ev") for r in self.hub_diag_rows if _is_page_federation_row(r)]
        self.assertIn("close", control, "the page filed the relay socket's close (the positive control over a live read): %r" % (control,))
        self.assertGreaterEqual(control.count("open"), 2, "…and both opens, the redial's included: %r" % (control,))
        bad = [r for r in self.hub_diag_rows
               if r.get("surface") == "federation" and r.get("what") in ("feedDelta-nobase", "feedDelta-stale")]
        self.assertEqual(bad, [], "the redialed socket's first frame seeded its base and nothing was refused by the gen gate")


if __name__ == "__main__":
    unittest.main()
