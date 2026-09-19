"""A federated chat pane dials the remote with the PAGE'S OWN terms (the design in
plans/federated-pane-dial-terms.md; the code it decides). Two hermetic kernels on one box:
a hub that owns no session and a checked-in TESTHOST that owns two ("api" the watched tab, "worker" a cold
one). The hub's /chat page, in a skeleton posture (?skeleton=1) with the watched tab persisted as a REMOTE
session, dials TESTHOST's relay socket. Before this change the remote dial carried only app+wid, so the
remote built every tab whole, held no skeleton set, and filed an anonymous relay row: the cost the user's
long chat thread ran on. Now federation.ts reads the shim's __rompDialTerms and carries them to each remote
socket, so the remote is served the way the local pane is.

Red first at the base (the bare dial), green with the terms, on three observables:
  1. the relay dial URL (window.__dials) carries skeleton=1, delta=1, the watched tab's BARE sid as
     active=, and an iid namespaced by the hub's wid;
  2. the REMOTE kernel's /perf builds.chat.coldSkipped is >0 (it dieted the cold tab for the hub's
     skeleton client), 0 at the base;
  3. the REMOTE kernel's client-diag.jsonl carries a wsopen row of kind "relay" whose iid presence flag is
     true (the stored row records iid as present/absent, not the value: kernel.py _note_ws_open), where the
     bare dial left it the absent one that reads as an anonymous relay.

A second pass (review round 3 of the lazy panes, 2026-09-19): the hub's SHELL at a phone viewport, a cold open with
the remote attached, the stored tab the remote's `api`. The phone's chat pane dials its LOCAL socket with skeleton=1
(the fork's phone diet) at the shim's parse; federation.ts dials the relay only after its async /tunnels poll, by
which time the local socket has opened and the shim's __rompDialTerms answers skeleton 0 (its term is scoped to the
first local dial through !everConnected), so the relay dial carries active=<api> and NO skeleton and the remote serves
its whole board through the relay: the order is recorded (the relay's dial stamp against the local socket's open), the
remote's coldSkipped does not move across the pass, and no TESTHOST tab lands as a skeleton. The pin reads the dial's
skeleton, active, delta, iid and wid, and deliberately not `caps` (PR 815 adds a constant caps term to the same URL).

This lab boots subprocess kernels and drives Chromium; it loads no romp code in-process, so it carries no
in-process state-isolation preamble and is not scanned by tests/test_state_isolation_order.py (the same as
tests/test_chat_split_host_served.py, its two-kernel sibling). Synthetic only: placeholder uuids, hostname
TESTHOST, invented transcript text.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes)

SID_R0 = "11111111-2222-4333-8444-000000000701"   # "api" on TESTHOST: the tab the page is watching
SID_R1 = "11111111-2222-4333-8444-000000000702"   # "worker" on TESTHOST: a cold tab the skeleton client diets
HOST = "TESTHOST"
REMOTE0 = HOST + ":" + SID_R0                      # …as the hub's dashboard carries it (federation.ts prefixId)
WID = "hublab"                                     # the hub pane's wid: the iid it sends is namespaced by this


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _transcript(sid, tag, cwd, pairs):
    """`pairs` CLOSED user/assistant turns for `sid` (an OPEN turn would invite the boot reconcile to resume it)."""
    out, parent = [], None
    filler = ["The ranking pass reads its weights from the notes-api config now.",
              "Tokenizer edge cases (hyphens, quotes) are covered by the new fixture set.",
              "Index rebuild time is dominated by the stemmer; caching its table halves it."]
    for i in range(pairs):
        u, a = "%s-u%02d" % (tag, i), "%s-a%02d" % (tag, i)
        out.append({"type": "user", "uuid": u, "parentUuid": parent, "sessionId": sid, "cwd": cwd,
                    "timestamp": "2024-01-01T00:%02d:00Z" % (i % 60), "promptSource": "typed",
                    "message": {"role": "user", "content": "turn %d: what changed in the notes-api search?" % i}})
        out.append({"type": "assistant", "uuid": a, "parentUuid": u, "sessionId": sid, "cwd": cwd,
                    "timestamp": "2024-01-01T00:%02d:30Z" % (i % 60),
                    "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                                "content": [{"type": "text", "text": filler[i % len(filler)]}]}})
        parent = a
    return "".join(json.dumps(r) + "\n" for r in out)


def _kernel(lab, name, port, token, sessions):
    """Boot one hermetic kernel: its own state root and dist, and `sessions` [(sid, name, tag)] with closed-turn transcripts."""
    state = os.path.join(lab, name, "xdg", "romp")
    claude = os.path.join(lab, name, "claude")
    cwd = os.path.join(lab, name, "proj")
    for d in ("names", "sdk", "states"):
        os.makedirs(os.path.join(state, d), exist_ok=True)
    os.makedirs(cwd, exist_ok=True)
    Path(state, "session-hosts").write_text("off\n")   # a lab root writes its own hosts off (the conftest rule)
    Path(state, "usage.json").write_text(json.dumps({"five_hour": {"pct": 100}, "seven_day": {"pct": 10}}))   # park sends
    proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
    os.makedirs(proj, exist_ok=True)
    for sid, sname, tag in sessions:
        Path(state, "names", sid).write_text("%s\t%s\t\t\n" % (sname, cwd))
        Path(state, "sdk", sid + ".json").write_text(json.dumps(
            {"sid": sid, "name": sname, "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": sid, "alive": True}))
        Path(proj, sid + ".jsonl").write_text(_transcript(sid, tag, cwd, 6))
    env = _lab.kernel_env(os.path.join(lab, name), claude, os.path.join(lab, "dist"), port, token, ROMP_HOST_NAME=name.upper())
    log = os.path.join(lab, name + "-kernel.log")
    proc = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(log, "w"), stderr=subprocess.STDOUT, env=env)
    for _ in range(120):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/healthz" % port, timeout=1)
            return proc, log
        except Exception:
            time.sleep(0.5)
    proc.kill(); proc.wait()
    raise unittest.SkipTest("hermetic kernel %s never served /healthz here" % name)


# The Chromium driver: hook every socket URL the page dials (window.__dials), persist the watched tab as a
# REMOTE session before the page's scripts run (the shim's ?active= and __rompDialTerms read it), open the
# hub's /chat page in a skeleton posture, and wait for the relay socket to the remote. The kernel-side
# observables (the remote's /perf and client-diag) are read from Python after this returns.
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
const page = await context.newPage();
const out = { dials: [], died: null, tabSeen: false };
page.on("pageerror", () => {});
await page.addInitScript(() => {
  window.__dials = []; const W = window.WebSocket;
  window.WebSocket = function (url, protos) { window.__dials.push(String(url)); return protos === undefined ? new W(url) : new W(url, protos); };
  window.WebSocket.prototype = W.prototype; window.WebSocket.CONNECTING = 0; window.WebSocket.OPEN = 1; window.WebSocket.CLOSING = 2; window.WebSocket.CLOSED = 3;
});
// the watched tab is a REMOTE session, host-prefixed as the dashboard carries it: __rompDialTerms carries it
// to the remote dial, where federation.ts strips the host to the bare sid the remote knows
await page.addInitScript((rid) => { try { localStorage.setItem("romp-vscode-state-chat", JSON.stringify({ activeId: rid })); } catch (e) {} }, cfg.remote0);
try {
  await page.goto(cfg.chat);
  // the FederationManager attaches every checked-in remote on load; wait for its relay socket to be dialed
  await page.waitForFunction(() => (window.__dials || []).some((u) => u.indexOf("/remote/TESTHOST/ws") !== -1), null, { timeout: 30000 });
  // the remote tab surfaces once the relay is open (best-effort confirmation; the assertions read __dials + the remote kernel)
  try { await page.locator("#tabs .tab", { hasText: "TESTHOST" }).first().waitFor({ timeout: 15000 }); out.tabSeen = true; } catch (e) {}
  // let the remote serve the skeleton client: the watched tab full, the cold tab skipped, the relay wsopen row filed
  await page.waitForTimeout(3000);
  out.dials = await page.evaluate(() => (window.__dials || []).slice());
} catch (e) {
  out.died = String(e).slice(0, 400);
  try { out.dials = await page.evaluate(() => (window.__dials || []).slice()); } catch (e2) {}
}
console.log("RESULT:" + JSON.stringify(out));
await browser.close();
"""


# The phone-shell pass (review round 3, regression-2): the hub's SHELL (`/?token=`) at an iPhone viewport, the stored tab
# the REMOTE's api. Every WebSocket any document of the page constructs is recorded on the top window with the document
# that dialed it, the dial's stamp and the open's stamp (same origin), so the chat pane's LOCAL dial, its open and its
# RELAY dial can be ordered; the strip is read for the remote's tabs and whether any landed as a skeleton.
DRIVER_PHONE = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium, devices } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(cfg.launch || {}); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const dev = { ...(devices["iPhone 14"] || {}) }; delete dev.defaultBrowserType;
const context = await browser.newContext({ ...dev, viewport: { width: 390, height: 844 } });
const out = { wire: [], died: null, remoteTabs: null, mobileShell: null };
// in every document (the shell and each pane): wrap the WebSocket constructor so each dial is recorded on the TOP window with
// its document, its stamp and its open's stamp; the top document also seeds the chat blob with the REMOTE tab as the one shown
await context.addInitScript((rid) => {
  try {
    const T = window.top; if (!T.__wire) T.__wire = [];
    const W = window.WebSocket;
    const Wrapped = function (url, protos) {
      const rec = { url: String(url), t: Date.now(), doc: location.pathname, openT: null };
      T.__wire.push(rec);
      const ws = protos === undefined ? new W(url) : new W(url, protos);
      ws.addEventListener("open", () => { rec.openT = Date.now(); });
      return ws;
    };
    Wrapped.prototype = W.prototype; Wrapped.CONNECTING = 0; Wrapped.OPEN = 1; Wrapped.CLOSING = 2; Wrapped.CLOSED = 3;
    window.WebSocket = Wrapped;
    if (window === window.top) localStorage.setItem("romp-vscode-state-chat", JSON.stringify({ activeId: rid }));
  } catch (e) {}
}, cfg.remote0);
const page = await context.newPage();
page.on("pageerror", () => {});
try {
  await page.goto(cfg.shell);
  // the chat pane's relay dial to the remote (federation.ts, after its /tunnels poll)
  await page.waitForFunction(() => (window.__wire || []).some((r) => r.doc === "/chat" && r.url.indexOf("/remote/TESTHOST/ws?app=chat") !== -1), null, { timeout: 30000 });
  out.mobileShell = await page.evaluate(() => !!document.getElementById("mtabs") && getComputedStyle(document.getElementById("mtabs")).display !== "none");
  const chat = () => page.frames().find((f) => { try { return new URL(f.url()).pathname === "/chat"; } catch (e) { return false; } });
  const readTabs = () => { const f = chat(); return f ? f.evaluate(() => Array.from(document.querySelectorAll("#tabs .tab[data-id]")).map((t) => ({ id: t.dataset.id, skeleton: t.classList.contains("tab-skeleton"), active: t.classList.contains("active") }))).catch(() => null) : Promise.resolve(null); };
  // the remote's two tabs on the strip, neither a skeleton (bounded; what stood at the deadline is what is asserted)
  const deadline = Date.now() + 30000; let tabs = null;
  while (Date.now() < deadline) { tabs = await readTabs(); if (tabs && tabs.filter((t) => t.id.indexOf("TESTHOST:") === 0).length >= 2 && tabs.every((t) => !t.skeleton)) break; await page.waitForTimeout(150); }
  await page.waitForTimeout(3000);   // the remote's push cycle: its relay wsopen row filed, its builds counted
  out.remoteTabs = await readTabs();
  out.wire = await page.evaluate(() => (window.__wire || []).slice());
} catch (e) {
  out.died = String(e).slice(0, 400);
  try { out.wire = await page.evaluate(() => (window.__wire || []).slice()); } catch (e2) {}
}
console.log("RESULT:" + JSON.stringify(out));
await browser.close();
"""


class FederatedDialTerms(unittest.TestCase):
    """Two kernels (a hub and a checked-in TESTHOST), two driver runs in setUpClass (the standalone skeleton page, then the phone
    shell's cold open, one browser at a time); each method asserts one observable."""
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
        cls.lab = tempfile.mkdtemp(prefix="federated-dial-terms-")
        lab_dist.copy_dist(os.path.join(cls.lab, "dist"))   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        # the REMOTE owns both sessions (the watched tab + a cold one); the HUB owns none and shows them through the relay
        cls.rport, cls.rtoken = _free_port(), "testtok-remote-fed"
        cls.hport, cls.htoken = _free_port(), "testtok-hub-fed"
        rp, cls.rlog = _kernel(cls.lab, "testhost", cls.rport, cls.rtoken, [(SID_R0, "api", 1), (SID_R1, "worker", 2)])
        cls.procs.append(rp)
        hp, cls.hlog = _kernel(cls.lab, "hub", cls.hport, cls.htoken, [])
        cls.procs.append(hp)
        body = json.dumps({"host": HOST, "kernelPort": cls.rport, "busPort": _free_port(), "token": cls.rtoken}).encode()
        req = urllib.request.Request("http://127.0.0.1:%d/checkin?token=%s" % (cls.hport, cls.htoken), data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            ans = json.loads(resp.read().decode())
        if not ans.get("ok"):
            raise unittest.SkipTest("the hub refused the check-in: %r" % ans)
        rows = []
        for _ in range(60):   # the hub's supervisor probes the peer and reports it up; the browser dials only then
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/tunnels?token=%s" % (cls.hport, cls.htoken), timeout=3) as r2:
                    rows = json.loads(r2.read().decode()).get("tunnels") or []
            except Exception:
                rows = []
            row = next((t for t in rows if t.get("host") == HOST), None)
            if row and row.get("status") == "up" and row.get("hasToken"):
                break
            time.sleep(0.5)
        else:
            raise unittest.SkipTest("the hub never reported the checked-in peer up: %r" % (rows,))
        cls.result, cls.driver_error = None, None
        cls._drive()
        cls.remote_chat_perf = cls._poll_remote_chat_perf()
        cls.remote_relay_rows = cls._read_relay_wsopen_rows()
        # the phone-shell pass (review round 3): the remote's counters read before and after it, once they hold still, so the
        # pass's own effect is the difference (the first pass left coldSkipped above 0 and one relay row)
        cls.phone_cold_before = cls._settled_remote_chat_perf()
        cls.phone_relay_rows_before = len(cls._read_relay_wsopen_rows())
        cls.phone_result, cls.phone_error = None, None
        cls._drive_phone()
        cls.phone_relay_rows_after = len(cls._relay_wsopen_rows_at_least(cls.phone_relay_rows_before + 1))
        cls.phone_cold_after = cls._settled_remote_chat_perf()

    @classmethod
    def _drive(cls):
        cfg = os.path.join(cls.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump({"chat": "http://127.0.0.1:%d/chat?skeleton=1&wid=%s&token=%s" % (cls.hport, WID, cls.htoken),
                       "remote0": REMOTE0}, f)
        driver = os.path.join(cls.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        try:
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=240,
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
    def _drive_phone(cls):
        cfg = os.path.join(cls.lab, "cfg-phone.json")
        with open(cfg, "w") as f:
            json.dump({"shell": "http://127.0.0.1:%d/?token=%s" % (cls.hport, cls.htoken), "remote0": REMOTE0}, f)
        driver = os.path.join(cls.lab, "driver-phone.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER_PHONE)
        try:
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=240,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        except subprocess.TimeoutExpired as e:
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            cls.phone_error = "phone driver timed out; partial output:\n%s" % so
            return
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box, the served leg needs one (CI installs none)")
        if p.returncode != 0:
            cls.phone_error = "phone driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:]
            return
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        if line is None:
            cls.phone_error = "phone driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:]
            return
        cls.phone_result = json.loads(line[len("RESULT:"):])

    @classmethod
    def _remote_chat_perf_once(cls):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/perf?token=%s" % (cls.rport, cls.rtoken), timeout=3) as r:
                perf = json.loads(r.read().decode())
            return (perf.get("builds") or {}).get("chat") or {}
        except Exception:
            return {}

    @classmethod
    def _settled_remote_chat_perf(cls):
        """The remote's builds.chat once two reads 0.7 s apart agree (the lab is quiet: no CLI, no live turn), bounded; the last
        read otherwise. A before/after pair of these makes one pass's effect readable on cumulative counters."""
        last = cls._remote_chat_perf_once()
        for _ in range(14):
            time.sleep(0.7)
            cur = cls._remote_chat_perf_once()
            if cur and cur == last:
                return cur
            last = cur
        return last

    @classmethod
    def _relay_wsopen_rows_at_least(cls, n):
        """The remote's relay wsopen rows once at least `n` are on file (bounded); what is on file otherwise."""
        rows = []
        for _ in range(40):
            rows = cls._read_relay_wsopen_rows()
            if len(rows) >= n:
                break
            time.sleep(0.3)
        return rows

    @classmethod
    def _poll_remote_chat_perf(cls):
        """The remote's builds.chat counters, once its push cycle has served the hub's skeleton client (a bounded
        retry, as the /tunnels poll above: no busy loop). At the base the dial states no diet and coldSkipped stays 0."""
        chat = {}
        for _ in range(20):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/perf?token=%s" % (cls.rport, cls.rtoken), timeout=3) as r:
                    perf = json.loads(r.read().decode())
                chat = (perf.get("builds") or {}).get("chat") or {}
            except Exception:
                chat = {}
            if chat.get("coldSkipped"):
                break
            time.sleep(0.5)
        return chat

    @classmethod
    def _read_relay_wsopen_rows(cls):
        """The remote kernel's wsopen rows of kind 'relay' (the hub's spliced dial). data.iid is a PRESENCE flag,
        not the value (kernel.py _note_ws_open): true names a per-pane iid, false is the anonymous relay."""
        path = os.path.join(cls.lab, "testhost", "xdg", "romp", "client-diag.jsonl")
        rows = []
        for _ in range(20):
            rows = []
            try:
                with open(path) as fh:
                    for ln in fh:
                        try:
                            rec = json.loads(ln)
                        except ValueError:
                            continue
                        if rec.get("what") == "wsopen" and (rec.get("data") or {}).get("kind") == "relay":
                            rows.append(rec)
            except OSError:
                rows = []
            if rows:
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

    def _driver_ran(self):
        if getattr(type(self), "driver_error", None):
            self.fail(type(self).driver_error)
        if getattr(type(self), "result", None) is None:
            raise unittest.SkipTest("the driver produced no result")

    def _relay_dial(self):
        self._driver_ran()
        relay = [u for u in self.result["dials"] if "/remote/TESTHOST/ws" in u]
        self.assertTrue(relay, "the hub page dialed the remote's relay socket: %r" % self.result["dials"])
        return relay[0]

    def test_the_hub_dials_the_remote_relay_socket(self):
        self.assertTrue(self._relay_dial())

    def test_the_remote_dial_carries_the_pages_terms(self):
        qs = parse_qs(urlsplit(self._relay_dial()).query)
        self.assertEqual(qs.get("app"), ["chat"], "the pane's app")
        self.assertEqual(qs.get("delta"), ["1"], "delta rides every dial, as the local pane's does")
        self.assertEqual(qs.get("skeleton"), ["1"], "the page's skeleton posture rode the remote dial")
        self.assertEqual(qs.get("active"), [SID_R0], "the watched remote tab, stripped to its bare sid")

    def test_the_remote_iid_is_namespaced_by_the_hub_wid(self):
        qs = parse_qs(urlsplit(self._relay_dial()).query)
        iid = (qs.get("iid") or [""])[0]
        self.assertTrue(iid.startswith(WID + ":"),
                        "the iid a hub pane sends is namespaced by its wid so it cannot collide with the remote's own page: %r" % iid)
        self.assertGreater(len(iid), len(WID) + 1, "…and carries the page's own instance id after the prefix")

    def test_the_remote_diets_its_cold_tab_for_the_skeleton_client(self):
        self._driver_ran()
        self.assertGreater(self.remote_chat_perf.get("coldSkipped") or 0, 0,
                           "the remote skipped its cold tab for the hub's skeleton client: %r" % self.remote_chat_perf)

    def test_the_remote_relay_wsopen_row_names_a_per_pane_iid(self):
        self._driver_ran()
        rows = self.remote_relay_rows
        self.assertTrue(rows, "the remote filed a relay wsopen row for the hub's spliced dial")
        self.assertTrue(any((r.get("data") or {}).get("iid") for r in rows),
                        "a relay row names a per-pane iid (present), not the absent one that reads as an anonymous relay: %r"
                        % [r.get("data") for r in rows])

    # ---- the phone shell's cold open with the remote attached (review round 3 of the lazy panes, regression-2) ----
    def _phone_ran(self):
        if getattr(type(self), "phone_error", None):
            self.fail(type(self).phone_error)
        r = getattr(type(self), "phone_result", None)
        if r is None:
            raise unittest.SkipTest("the phone driver produced no result")
        self.assertIsNone(r.get("died"), "the phone driver died: %r" % r.get("died"))
        self.assertTrue(r.get("mobileShell"), "the viewport selected the phone shell (the tab bar shows)")
        return r

    def _phone_chat_dials(self):
        """The chat pane's first LOCAL dial and its first RELAY dial to TESTHOST, from the wire the driver recorded; both lists
        are guarded non-empty before anything is compared."""
        r = self._phone_ran()
        wire = r.get("wire") or []
        self.assertTrue(wire, "the page dialed at least one socket")
        local = [w for w in wire if w.get("doc") == "/chat" and "/ws?app=chat" in w.get("url", "") and "/remote/" not in w.get("url", "")]
        relay = [w for w in wire if w.get("doc") == "/chat" and "/remote/TESTHOST/ws?app=chat" in w.get("url", "")]
        self.assertTrue(local, "the chat pane dialed its local socket: %r" % [w.get("url") for w in wire])
        self.assertTrue(relay, "the chat pane dialed the remote's relay socket: %r" % [w.get("url") for w in wire])
        return local[0], relay[0]

    def test_a_phone_cold_open_dials_the_local_chat_with_skeleton_1_and_the_relay_without_it_after_the_local_open(self):
        local, relay = self._phone_chat_dials()
        lq = parse_qs(urlsplit(local["url"]).query)
        self.assertEqual(lq.get("skeleton"), ["1"], "the phone's first LOCAL chat dial takes the diet (the fork's RESTART_DIET line): %r" % local["url"])
        self.assertEqual(lq.get("active"), [REMOTE0], "the stored tab rides the local dial host-prefixed, as the dashboard carries it")
        self.assertNotIn("reconnect", lq, "a first dial")
        self.assertIsNotNone(local.get("openT"), "the local socket opened (the open's stamp is on the record): %r" % (local,))
        rq = parse_qs(urlsplit(relay["url"]).query)
        self.assertEqual(rq.get("app"), ["chat"])
        self.assertEqual(rq.get("delta"), ["1"], "delta rides the relay dial, as the local one")
        wid = (rq.get("wid") or [""])[0]
        self.assertTrue(wid, "the relay dial carries the dashboard's wid: %r" % relay["url"])
        self.assertTrue((rq.get("iid") or [""])[0].startswith(wid + ":"), "the iid is namespaced by that wid: %r" % rq.get("iid"))
        self.assertEqual(rq.get("active"), [SID_R0], "the stored tab is this host's, stripped to its bare sid")
        self.assertNotIn("skeleton", rq, "the relay dial carries NO skeleton term: the shim's __rompDialTerms scopes the phone diet to the first local dial (!everConnected), and the relay is dialed after the local open: %r" % relay["url"])
        self.assertNotIn("reconnect", rq, "a first relay dial")
        # the order the comment in kernel.py states, recorded: the relay's dial after the local socket's open
        self.assertGreater(relay["t"], local["openT"], "the relay was dialed %d ms after the local dial and %d ms after its open; the comment's order holds"
                           % (relay["t"] - local["t"], relay["t"] - local["openT"]))

    def test_a_phone_cold_open_is_served_the_remotes_whole_board_through_the_relay(self):
        r = self._phone_ran()
        cls = type(self)
        self.assertGreaterEqual(cls.phone_relay_rows_after, cls.phone_relay_rows_before + 1,
                                "the remote accepted the phone pane's relay socket (a relay wsopen row of its own): %d before, %d after" % (cls.phone_relay_rows_before, cls.phone_relay_rows_after))
        tabs = r.get("remoteTabs") or []
        remote = [t for t in tabs if str(t.get("id", "")).startswith(HOST + ":")]
        self.assertEqual(sorted(t["id"] for t in remote), sorted([REMOTE0, HOST + ":" + SID_R1]), "the remote's two tabs are on the phone's strip: %r" % (tabs,))
        self.assertEqual([t["id"] for t in remote if t.get("skeleton")], [], "none of them landed as a skeleton: the remote served its whole board (no skeleton term on the relay dial, so no diet): %r" % (remote,))
        before, after = cls.phone_cold_before.get("coldSkipped"), cls.phone_cold_after.get("coldSkipped")
        self.assertIsInstance(before, int); self.assertIsInstance(after, int)
        self.assertEqual(after, before, "the remote skipped no cold tab for the phone's relay client (the first pass's %d stand): %r -> %r" % (before, cls.phone_cold_before, cls.phone_cold_after))


if __name__ == "__main__":
    unittest.main()
