"""A federated hub's timeline page draws a REMOTE host's appended bar from that host's bars slot patch (2026-09-19).

Two hermetic kernels on one box: a hub that owns no session and a checked-in TESTHOST that owns eight ("api",
"worker" and the notes-api demo's six others), each seeded with six closed turns stamped inside the last 90 minutes,
so the hub's timeline page shows a board of the last hours in plain time (the pane's default view collapses idle
gaps and drew the siblings' 2024 seed just the same, 6 bars then 7, in the drive that checked; the kernel filters no
bar by time). The hub's /timeline page dials TESTHOST's relay socket with the page's own
terms (app=timeline, delta=1 and federation's caps=feedDelta), so after the relay socket holds the remote's whole
bars frame the remote serves every change to its bars as a {type:"delta", slot:"bars"} patch (_send_slot_delta),
which the conn's view-delta receiver reassembles (ui/webview/view-deltas.ts via Conn.viewDeltas) and the timeline's
bars arm merges and draws. The change is one closed user/assistant pair appended to api's transcript on the remote,
through the kernel's own road (its transcript tail: the pusher's view signature reads the transcript mtimes, the
rebuild mints one new bar, the bars fill splits it and the delta path sends the patch), never a POST.

Before the receiver (the branch at 7a7b31ed2, or main's bundle) the patch reached the page and vanished: federation.ts
had no arm for the type, the timeline boot's frame listener has none either, and no row was filed. The remote lane
froze at its first whole frame with nothing saying so (the bars twin of the Outline's delta-unapplied rows).

Five observables, green with the receiver:
  1. the relay dial URL (window.__dials) carries app=timeline, delta=1 and caps=feedDelta;
  2. the first relay bars frame is whole, with every one of the remote's eight lanes, and the hub's page draws the
     seed's six bars on the api lane (the door's positive control: the DOM count is read from the drawn SVG, the bars
     whose centre sits on the lane label's row, and cross-checked against the panel's own held lane through a trap on
     the page's connect hook);
  3. after the change the relay socket received a {type:"delta", slot:"bars"} patch whose turns collection sets a key
     for api's sid, no whole bars frame followed it, and the patch is under the kernel's size guard against the last
     whole frame it holds (_DELTA_MAX_FRACTION: the note that a small board sends an appended bar whole does not hold
     for this seed; the recorded lengths say by how much);
  4. the page draws the seventh bar on the api lane (the visible side), and the panel's held lane counts seven;
  5. the hub's client-diag carries the page's own federation rows about TESTHOST (the positive control for a negative
     read) and no needSlot left on either socket, no delta-unknown-slot row and no unapplied row: the patch applied.
Red before the receiver on 4 alone: the patch is on the wire (3 holds), the count stays six, and nothing is filed.
BarsFrozenBeforeReceiver states that freeze as a positive assertion against an old hub named by ROMP_CORNER_OLD_HUB_ROOT
(a kernel and PREBUILT vscode-extension/dist from before the receiver: main before PR 815, or the PR at 7a7b31ed2);
ROMP_CORNER_HUB_ROOT pointed at such a checkout is the main class's fails-before lever (4 goes red, the rest hold).
Both knobs are the corners lab's (tests/test_federated_capability_corners_served.py), so one environment drives both
labs; without a knob the frozen class skips as `optional:`, which CI's served switch leaves alone.
ROMP_CORNER_REPORT_DIR, when set, gets one JSON per class with everything recorded.

This lab boots subprocess kernels and drives Chromium; it loads no romp code in-process, so it carries no in-process
state-isolation preamble and is not scanned by tests/test_state_isolation_order.py (as its siblings). Synthetic only:
placeholder uuids, hostname TESTHOST, the notes-api demo's session names, invented turn text.
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
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_federated_dial_terms_served as _dial              # noqa: E402  the two-kernel boot, the seed and the change (the module, not its class)
import test_federated_capability_corners_served as _corners   # noqa: E402  the eight-session set, the knobs and the diag readers (the module, not its classes)

SID_R0 = _corners.SID_R0            # "api" on TESTHOST: the lane the change lands on
SID_R1 = _corners.SID_R1            # "worker" on TESTHOST
EXTRA = _corners.EXTRA              # six more, so the whole bars frame is many times one bar's patch
HOST = "TESTHOST"
WID = "hublab"
LANE = HOST + ":" + SID_R0          # the lane id on the hub (federation prefixes id AND name, _prefixIdBearing)
LANE_LABEL = HOST + ":api"          # its label's text: the quiet host tspan and the name tspan
SEED_AGO_S = 5400                   # the seed's first pair 90 min ago: every seed bar inside the pane's fitted window
SEED_BARS = _dial.SEED_PAIRS
SEP = "\u001f"                     # the unit separator (0x1F) as an escape, so the key assertion reads in a diff: a bars patch key is the bare sid, this separator and the bar id (_delta_split)
GUARD = 0.6                         # _DELTA_MAX_FRACTION: a patch this fraction of the whole frame goes whole instead
CHANGE_PROMPT = "a later turn: did the notes-api index rebuild finish?"
CHANGE_REPLY = "It finished; the stemmer table is cached now."


# The Chromium driver: hook every socket the page dials (window.__dials), every frame a relay socket receives with its
# type, slot and length (a bars frame's lane count; a patch's collections and the keys its turns collection sets) and
# every needSlot / needFullFeed / ready the page sends with the socket it left on; trap the page's connect hook so the
# TimelinePanel is reachable (window.__tlPanel); count the drawn bars on one lane from the SVG (window.__barCount: the
# coloured rects in the plot group whose centre sits on the lane label's row; only bars inside the window are drawn,
# which is what "visible" means here). Open the hub's timeline page, wait for the relay's whole bars frame and the
# seed's bars on the lane, wait for the relay to go quiet (the ready handshake's own re-based frames must not carry the
# change), append the pair, wait for the seventh bar, report. Kernel-side observables (the remote's /perf, the hub's
# client-diag) are read from Python.
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
const out = { dials: [], frames: [], sends: [], seedBars: null, seedPanelBars: null, quiet: false, before: null, fullLen: null,
              barsBefore: null, appended: null, barSeenMs: null, barsAfter: null, panelBarsAfter: null, laneKeys: null, pane: null, died: null };
page.on("pageerror", () => {});
await page.addInitScript((o) => {
  window.__dials = []; window.__frames = []; window.__sends = []; const W = window.WebSocket;
  const strip = (u) => o.stripDelta && u.indexOf("/remote/") !== -1 ? u.replace(/([?&])delta=1&?/, (m, sep) => sep).replace(/[?&]$/, "") : u;
  window.WebSocket = function (url, protos) {
    const u = strip(String(url));
    window.__dials.push(u);
    const relay = u.indexOf("/remote/") !== -1;
    const w = protos === undefined ? new W(u) : new W(u, protos);
    const idx = window.__dials.length - 1;
    if (relay) {
      w.addEventListener("message", (ev) => {
        try {
          const m = JSON.parse(ev.data);
          if (!m || m.type === "ka") return;
          const f = { sock: idx, t: String(m.type), slot: m.slot ? String(m.slot) : "", len: String(ev.data).length, at: Date.now() };
          if (m.type === "bars") f.lanes = Object.keys(m.turns || {}).length;
          if (m.type === "delta") {
            f.coll = Object.keys(m.coll || {}); f.restKeys = Object.keys(m.rest || {}); f.restAll = !!m.restAll; f.base = m.base; f.rev = m.rev;
            const set = ((m.coll || {}).turns || {}).set; f.setKeys = set ? Object.keys(set) : [];
          }
          window.__frames.push(f);
        } catch (e) {}
      });
    }
    const send = w.send.bind(w);
    w.send = (d) => {
      try { const m = JSON.parse(d); if (m && (m.type === "needSlot" || m.type === "needFullFeed" || m.type === "ready")) window.__sends.push({ sock: relay ? "relay" : "local", type: m.type, slot: m.slot ? String(m.slot) : "" }); } catch (e) {}
      return send(d);
    };
    return w;
  };
  window.WebSocket.prototype = W.prototype; window.WebSocket.CONNECTING = 0; window.WebSocket.OPEN = 1; window.WebSocket.CLOSING = 2; window.WebSocket.CLOSED = 3;
  // the panel door: the page's boot assigns window.__rompConnectTimeline and then calls it with its TimelinePanel; the
  // trap keeps the panel as window.__tlPanel, whose _turnsRaw() is the merged lane as held (the DOM count's cross-check)
  Object.defineProperty(window, "__rompConnectTimeline", { configurable: true, get() { return undefined; },
    set(fn) { Object.defineProperty(window, "__rompConnectTimeline", { configurable: true, writable: true, value: (p) => { window.__tlPanel = p; return fn(p); } }); } });
  // the drawn bars on the lane whose label reads `label`: -1 without the label
  window.__barCount = (label) => {
    const lbl = [...document.querySelectorAll("svg text")].find((t) => t.textContent === label);
    if (!lbl) return -1;
    const laneY = parseFloat(lbl.getAttribute("y")) - 3.5;
    return [...document.querySelectorAll('g[data-tl-plot="1"] > rect')].filter((r) => {
      const f = r.getAttribute("fill");
      if (!f || f === "transparent" || f === "none" || f.indexOf("url(") === 0) return false;
      const y = parseFloat(r.getAttribute("y")), h = parseFloat(r.getAttribute("height"));
      return Math.abs(y + h / 2 - laneY) < 1;
    }).length;
  };
  window.__panelCount = (lane) => {
    const p = window.__tlPanel; if (!p) return null;
    const t = p._turnsRaw()[lane]; return Array.isArray(t) ? t.length : (t === undefined ? null : -1);
  };
}, { stripDelta: !!cfg.stripDelta });
const snap = () => page.evaluate(() => ({ dials: (window.__dials || []).slice(), frames: (window.__frames || []).slice(), sends: (window.__sends || []).slice() }));
const count = () => page.evaluate((l) => window.__barCount(l), cfg.laneLabel);
const panelCount = () => page.evaluate((l) => window.__panelCount(l), cfg.lane);
try {
  await page.goto(cfg.url);
  await page.bringToFront();   // the pane defers its draw while the document is hidden (_hiddenForPaint)
  await page.waitForFunction(() => (window.__dials || []).some((u) => u.indexOf("/remote/TESTHOST/ws") !== -1), null, { timeout: 30000 });
  await page.waitForFunction(() => (window.__frames || []).some((f) => f.t === "bars"), null, { timeout: 30000 });
  try { await page.waitForFunction(([l, n]) => window.__barCount(l) === n, [cfg.laneLabel, cfg.seedBars], { timeout: 20000 }); } catch (e) {}
  out.seedBars = await count(); out.seedPanelBars = await panelCount();
  // quiet = no new frame on the relay for 2 s (the pusher's steady state), up to 15 s
  for (let i = 0; i < 7; i++) {
    const n1 = (await snap()).frames.length;
    await page.waitForTimeout(2000);
    if ((await snap()).frames.length === n1) { out.quiet = true; break; }
  }
  const s0 = await snap();
  out.before = s0.frames.length;   // frames past this index came after the change
  const fulls = s0.frames.filter((f) => f.t === "bars");
  out.fullLen = fulls.length ? fulls[fulls.length - 1].len : null;   // the whole frame the remote holds as this socket's base
  out.barsBefore = await count();
  const t0 = Date.now();
  fs.appendFileSync(cfg.transcript.path, cfg.transcript.text);
  out.appended = cfg.transcript.text.length;
  await page.bringToFront();
  try { await page.waitForFunction(([l, n]) => window.__barCount(l) === n, [cfg.laneLabel, cfg.seedBars + 1], { timeout: cfg.waitMs }); out.barSeenMs = Date.now() - t0; } catch (e) {}
  await page.waitForTimeout(1500);   // let the rows land on the hub, and any frame the change earned
  out.barsAfter = await count(); out.panelBarsAfter = await panelCount();
  out.laneKeys = await page.evaluate(() => { const p = window.__tlPanel; return p ? Object.keys(p._turnsRaw()) : null; });
  // the lane as held and the pane's window, for the record: each bar's [start, end] against the pane's clock
  out.pane = await page.evaluate((l) => { const p = window.__tlPanel; if (!p) return null;
    return { now: p.data && p.data.now, winSec: p.winSec(), offSec: p.offSec(), bars: (p._turnsRaw()[l] || []).map((b) => [b.start, b.end]) }; }, cfg.lane);
  Object.assign(out, await snap());
} catch (e) {
  out.died = String(e).slice(0, 400);
  try { Object.assign(out, await snap()); } catch (e2) {}
}
console.log("RESULT:" + JSON.stringify(out));
await browser.close();
"""


class _BarsLab(unittest.TestCase):
    """Two kernels, the hub's timeline page, one change; each method asserts one observable."""
    maxDiff = None
    hub_root = None          # the hub kernel's checkout (bin/) and, when not None, its PREBUILT vscode-extension/dist
    seed_ago_s = SEED_AGO_S  # None keeps the seed's 2024 stamps (drawn too, under the pane's collapsed gaps; the record reads worse)
    strip_delta = False      # the page strips delta=1 from the relay dial: the remote serves whole frames
    wait_ms = 20000

    @classmethod
    def setUpClass(cls):
        if cls is _BarsLab:
            raise unittest.SkipTest("the base class")
        cls.procs = []
        try:
            cls._boot()
        except BaseException:          # a skip OR a failure: never leave a kernel or a lab behind
            cls.tearDownClass()
            raise

    @classmethod
    def _knobs(cls):
        cls.hub_root = _corners._root_knob("ROMP_CORNER_HUB_ROOT")

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here), the served lab needs them")
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            raise unittest.SkipTest("no playwright browser on this box, the served lab needs one (CI installs none)")
        cls._knobs()
        if cls.hub_root and not os.path.isfile(os.path.join(cls.hub_root, "bin", "romp-kernel")):
            raise unittest.SkipTest("no bin/romp-kernel under %s" % cls.hub_root)
        cls.lab = tempfile.mkdtemp(prefix="federated-bars-")
        if cls.hub_root:
            src = os.path.join(cls.hub_root, "vscode-extension", "dist")
            if not os.path.isfile(os.path.join(src, "federation.js")):
                raise unittest.SkipTest("no prebuilt dist under %s (build the extension there first)" % cls.hub_root)
            lab_dist.copy_prebuilt(src, os.path.join(cls.lab, "dist"))
        else:
            lab_dist.copy_dist(os.path.join(cls.lab, "dist"))   # the checkout's ONE build of the bundles, copied under its lock
        for name in ("testhost", "hub"):
            root = _corners._state_root(cls.lab, name)
            os.makedirs(root, exist_ok=True)
            Path(root, "update-mode.json").write_text(json.dumps({"mode": "off"}))   # a vintage without ROMP_UPDATE_CHECK reads the file
        cls.rport, cls.rtoken = _dial._free_port(), "testtok-remote-bars"
        cls.hport, cls.htoken = _dial._free_port(), "testtok-hub-bars"
        t0 = time.time() - cls.seed_ago_s if cls.seed_ago_s else None
        rp, cls.rlog = _dial._kernel(cls.lab, "testhost", cls.rport, cls.rtoken, [(SID_R0, "api", 1), (SID_R1, "worker", 2)] + EXTRA, t0=t0)
        cls.procs.append(rp)
        hp, cls.hlog = _dial._kernel(cls.lab, "hub", cls.hport, cls.htoken, [], bin_dir=os.path.join(cls.hub_root or ROOT, "bin"))
        cls.procs.append(hp)
        _dial.checkin(cls.hport, cls.htoken, cls.rport, cls.rtoken)
        cls.result, cls.driver_error = None, None
        cls._drive()
        cls.remote_sends, cls.remote_wire = cls._remote_perf()
        cls.hub_diag_rows = _corners.read_hub_diag_rows(cls.lab)
        cls._report()

    @classmethod
    def _transcript_change(cls):
        """The pair appended to api's transcript on the remote (the change): located as the kernel laid it out."""
        cwd = os.path.join(cls.lab, "testhost", "proj")
        proj = os.path.join(cls.lab, "testhost", "claude", "projects")
        cands = [p for p in Path(proj).rglob(SID_R0 + ".jsonl")]
        if not cands:
            raise unittest.SkipTest("no transcript for the api session under %s" % proj)
        return {"path": str(cands[0]), "text": _dial.change_pair(SID_R0, 1, cwd, CHANGE_PROMPT, CHANGE_REPLY)}

    @classmethod
    def _drive(cls):
        cfg = os.path.join(cls.lab, "cfg.json")
        conf = {"url": "http://127.0.0.1:%d/timeline?wid=%s&token=%s" % (cls.hport, WID, cls.htoken),
                "lane": LANE, "laneLabel": LANE_LABEL, "seedBars": SEED_BARS, "waitMs": cls.wait_ms,
                "stripDelta": cls.strip_delta, "transcript": cls._transcript_change()}
        with open(cfg, "w") as f:
            json.dump(conf, f)
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
    def _remote_perf(cls):
        """The remote's send counters by kind and slot (sends.full/delta/deduped.timelinebars: count and bytes, the
        sender's own account of the bars slot) and its memos.wire counters, read once after the driver."""
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/perf?token=%s" % (cls.rport, cls.rtoken), timeout=5) as r:
                perf = json.loads(r.read().decode())
            sends = perf.get("sends") if isinstance(perf.get("sends"), dict) else {}
            return sends, ((perf.get("memos") or {}).get("wire")) or {}
        except Exception as e:
            return {}, {"error": str(e)}

    @classmethod
    def _report(cls):
        """Everything recorded, as one JSON per class under ROMP_CORNER_REPORT_DIR (the written record of a drive)."""
        d = (os.environ.get("ROMP_CORNER_REPORT_DIR") or "").strip()
        if not d:
            return
        os.makedirs(d, exist_ok=True)
        rows = {}
        for r in cls.hub_diag_rows:
            k = "%s/%s" % (r.get("surface"), r.get("what"))
            rows[k] = rows.get(k, 0) + 1
        rec = {"lab": cls.__name__, "hub_root": cls.hub_root, "seed_ago_s": cls.seed_ago_s, "strip_delta": cls.strip_delta,
               "driver_error": cls.driver_error, "result": cls.result, "remote_sends": cls.remote_sends, "remote_wire": cls.remote_wire,
               "hub_diag_by_kind": rows,
               "federation_rows": [r.get("data") for r in cls.hub_diag_rows if r.get("surface") == "federation"][:12]}
        Path(d, cls.__name__ + ".json").write_text(json.dumps(rec, indent=1, sort_keys=True))

    @classmethod
    def tearDownClass(cls):
        for p in getattr(cls, "procs", []):
            try:
                p.kill(); p.wait()
            except Exception:
                pass
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    # ---- the readers ----
    def _driver_ran(self):
        if getattr(type(self), "driver_error", None):
            self.fail(type(self).driver_error)
        if getattr(type(self), "result", None) is None:
            raise unittest.SkipTest("the driver produced no result")
        if self.result.get("died"):
            self.fail("the driver died: %s" % self.result["died"])

    def _relay_dial(self):
        self._driver_ran()
        relay = [u for u in self.result["dials"] if "/remote/TESTHOST/ws" in u]
        self.assertTrue(relay, "the hub's timeline page dialed the remote's relay socket: %r" % self.result["dials"])
        return relay[0]

    def _frames(self):
        self._driver_ran()
        return self.result["frames"]

    def _kinds(self, frames=None):
        return [(f["t"], f["slot"]) for f in (self._frames() if frames is None else frames)]

    def _after_change(self):
        """The frames the relay socket received AFTER the change (the driver records the count at the change, once the
        relay had gone quiet)."""
        n = int(self.result.get("before") or 0)
        return self._frames()[n:]

    def _sends(self, sock, typ):
        self._driver_ran()
        return [s for s in self.result["sends"] if s["sock"] == sock and s["type"] == typ]

    def _bad_rows(self):
        return [(r.get("surface"), r.get("what"), r.get("data")) for r in self.hub_diag_rows if (r.get("surface"), r.get("what")) in _corners.BAD_ROWS]

    def _unknown_slot_rows(self):
        return [r.get("data") for r in self.hub_diag_rows if r.get("surface") == "federation" and (r.get("data") or {}).get("ev") == "delta-unknown-slot"]

    def _control(self):
        self._driver_ran()
        control = [r for r in self.hub_diag_rows if _corners.is_page_federation_row(r)]
        self.assertTrue(control, "the hub's client-diag carries the page's federation rows about TESTHOST (the posting road is live); "
                                 "by (surface, what): %r" % (sorted({(r.get("surface"), r.get("what")) for r in self.hub_diag_rows}),))

    def _bars_sends(self, kind):
        return ((self.remote_sends or {}).get(kind) or {}).get("timelinebars") or {}

    # ---- the assertions both classes share ----
    def _assert_dial(self, delta):
        qs = parse_qs(urlsplit(self._relay_dial()).query)
        self.assertEqual(qs.get("app"), ["timeline"], "the pane's app rides the relay dial")
        self.assertEqual(qs.get("delta"), (["1"] if delta else None), "the page's delta term on the relay dial (since 2026-09-15): %r" % qs)

    def _assert_seed_drawn(self):
        self._driver_ran()
        fulls = [f for f in self._frames() if f["t"] == "bars"]
        self.assertTrue(fulls, "the relay socket received the remote's whole bars frame: %r" % (self._kinds(),))
        self.assertEqual(fulls[0].get("lanes"), 2 + len(EXTRA), "the first whole frame carries every remote lane: %r" % (fulls[0],))
        self.assertEqual(self.result.get("seedBars"), SEED_BARS,
                         "the hub's page draws the seed's %d bars on the %s lane before the change (the door's positive control; "
                         "-1 = no such lane label; 0 = the label drawn, no bar on its row); lanes held: %r"
                         % (SEED_BARS, LANE_LABEL, self.result.get("laneKeys")))
        self.assertEqual(self.result.get("seedPanelBars"), SEED_BARS, "and the panel holds the same %d for the lane" % SEED_BARS)
        self.assertTrue(self.result.get("quiet"), "the relay went quiet before the change (no frame for 2 s within 15 s): %r" % (self._kinds(),))

    def _assert_patch_on_the_wire(self):
        after = self._after_change()
        patches = [f for f in after if (f["t"], f["slot"]) == ("delta", "bars")]
        self.assertTrue(patches, "the relay socket received the change as a bars slot patch; frames after the change: %r; all: %r"
                        % (self._kinds(after), self._kinds()))
        p = patches[0]
        self.assertIn("turns", p.get("coll") or [], "the patch changes the turns collection: %r" % (p,))
        keyed = [k.split(SEP) for k in p.get("setKeys") or []]   # exactly two parts around the separator: an empty SEP raises here, a wrong one splits nothing
        self.assertTrue(any(len(parts) == 2 and parts[0] == SID_R0 and parts[1] for parts in keyed),
                        "the patch sets a bar keyed as api's bare sid, the unit separator, the bar id: %r" % (p.get("setKeys"),))
        full = self.result.get("fullLen")
        self.assertTrue(full, "a whole bars frame was held before the change: %r" % (self._kinds(),))
        self.assertLess(p["len"], GUARD * full, "the patch (%d B) is under the size guard against the whole frame (%d B, %.2f of it)"
                        % (p["len"], full, p["len"] / float(full)))
        return patches, full


class FederatedBarsDelta(_BarsLab):
    """The receiver in place (this checkout on both sides): the remote's bars patch is reassembled and the hub's timeline
    draws the new bar on the remote lane. Red before the receiver on the drawn bar alone (ROMP_CORNER_HUB_ROOT at a hub
    from before it): the patch still crosses, nothing is filed, the lane stays at six."""

    def test_the_timeline_relay_dial_carries_the_pages_terms(self):
        self._assert_dial(delta=True)
        qs = parse_qs(urlsplit(self._relay_dial()).query)
        self.assertEqual(qs.get("caps"), ["feedDelta"], "federation's own cap rides every remote dial: %r" % qs)

    def test_the_seed_bars_are_drawn_on_the_remote_lane(self):
        self._assert_seed_drawn()

    def test_the_change_crossed_as_a_bars_patch_under_the_guard(self):
        patches, full = self._assert_patch_on_the_wire()
        after = self._after_change()
        self.assertEqual([f for f in after if f["t"] == "bars"], [],
                         "no whole bars frame followed the change on the relay socket (the patch applied; nothing asked for the slot): %r"
                         % (self._kinds(after),))

    def test_the_hub_draws_the_new_bar_on_the_remote_lane(self):
        self._driver_ran()
        self.assertIsNotNone(self.result.get("barSeenMs"),
                             "the seventh bar was drawn on the %s lane within %d ms of the append (count after the wait: %r, the panel's: %r; "
                             "frames after the change: %r)" % (LANE_LABEL, self.wait_ms, self.result.get("barsAfter"),
                                                                self.result.get("panelBarsAfter"), self._kinds(self._after_change())))
        self.assertEqual(self.result.get("barsAfter"), SEED_BARS + 1, "the lane shows %d bars after the change" % (SEED_BARS + 1))
        self.assertEqual(self.result.get("panelBarsAfter"), SEED_BARS + 1, "and the panel's held lane counts %d" % (SEED_BARS + 1))

    def test_nothing_asked_and_nothing_dropped(self):
        self._control()
        self.assertEqual(self._sends("relay", "needSlot"), [], "the receiver applied every patch: no resync asked of the remote")
        self.assertEqual(self._sends("local", "needSlot"), [], "nothing fell through to the pane: the LOCAL kernel was asked for no slot")
        self.assertEqual(self._unknown_slot_rows(), [], "no patch named a slot this side does not decode")
        self.assertEqual(self._bad_rows(), [], "no pane saw a raw patch")
        # recorded, not asserted (the sender's own account; the socket's frames above are the claim): the remote's
        # /perf sends for the bars slot, delta and full, are in the report


class BarsFrozenBeforeReceiver(_BarsLab):
    """The freeze this PR ends, as a positive statement against a hub from before the receiver (ROMP_CORNER_OLD_HUB_ROOT:
    a kernel and PREBUILT dist of main before PR 815, or of this PR at 7a7b31ed2): the remote serves the change as a
    bars patch, the old bundle decodes none and files nothing (federation.ts had no arm; the timeline boot drops the
    type in silence), no resync is asked of either kernel, and the remote lane stays at the seed's six bars for the
    whole wait. The bars twin of the Outline's frozen rows, with no row to show for it."""

    @classmethod
    def _knobs(cls):
        cls.hub_root = _corners._root_knob("ROMP_CORNER_OLD_HUB_ROOT")
        if not cls.hub_root:
            raise unittest.SkipTest("optional: ROMP_CORNER_OLD_HUB_ROOT unset: the frozen-bars corner needs a checkout of a hub from before the receiver, built")

    def test_the_relay_dial_carries_delta(self):
        self._assert_dial(delta=True)   # the caps term depends on the vintage (main: none; 7a7b31ed2: feedDelta) and is recorded, not asserted

    def test_the_seed_bars_are_drawn_on_the_remote_lane(self):
        self._assert_seed_drawn()

    def test_the_patch_crossed_and_was_dropped_in_silence(self):
        self._assert_patch_on_the_wire()
        self._control()
        self.assertIsNone(self.result.get("barSeenMs"), "the seventh bar never showed within %d ms" % self.wait_ms)
        self.assertEqual(self.result.get("barsAfter"), SEED_BARS, "the lane stands at the seed's %d bars after the change" % SEED_BARS)
        self.assertEqual(self.result.get("panelBarsAfter"), SEED_BARS, "the panel's held lane too: the patch never reached it")
        self.assertEqual(self._sends("relay", "needSlot"), [], "nothing asked of the remote")
        self.assertEqual(self._sends("local", "needSlot"), [], "nothing asked of the local kernel (no pane saw the patch)")
        self.assertEqual(self._bad_rows(), [], "no row: the timeline files none for a dropped patch")
        self.assertEqual(self._unknown_slot_rows(), [])


if __name__ == "__main__":
    unittest.main()
