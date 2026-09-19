"""The capability corners of the federated relay dial, driven for real (2026-09-19): what a hub's pages receive from a
remote kernel of each vintage, and what a user sees, with the hub's bundle new or old.

Since 8fe70da07 (2026-09-15) every relay dial carries the page's delta=1; since PR 815 it carries caps=feedDelta too
and federation.ts decodes whatever a remote sends: a remote that honours the cap sends {type:"feedDelta"} (applied per
host); one that ignores the cap but honours delta=1 sends {type:"delta", slot:"feed"} patches (reassembled per conn by
Conn.viewDeltas); one that ignores both sends whole {type:"feed"} frames (applied as before). An OLD hub bundle (main
before PR 815) dials delta=1 without caps and decodes no patch, so the same remote's rows freeze on its pages after
the first full frame: the Outline files a delta-unapplied row per dropped patch and posts a needSlot to the LOCAL
kernel, the feed and Waiting panes drop them silently. PR 815 changes no kernel, so it repairs that corner through the
hub's bundle alone: the hub box updates and the page reloads, and no remote needs a change for either slot. A remote-side
guard would also cover an old hub during a mixed-build window (the remote kernel reads relay=1 at accept, _dial_kind, and
picks the feed's protocol by the cap alone, so whole feed frames to a relay socket that announces no cap is a
one-condition change); it is not taken here: the old hub's timeline decodes no bars patch either, so a guard that covered
it whole would cost a whole bars frame per change on every old hub, and the hub's bundle is the one place both slots
are decoded.

Each class is one corner: two hermetic kernels (a hub owning no session, a checked-in TESTHOST owning eight sessions,
"api", "worker" and EXTRA's six), the hub's Waiting, Outline and feed pages (and its timeline, where the change is a
transcript append) in one Chromium, every socket's dial URL, inbound frame types and outbound asks (needSlot,
needFullFeed) recorded, then ONE change on the remote after every relay socket holds its full frame. The change is a
notice card (POST /notice, an asks-only change: the slot path's delta for it is one card against the whole frame,
under the size guard, so a caps-ignoring kernel emits a real patch; a todo changes the
frame's remainder and the guard sends a whole frame instead, which is why tests/test_federated_feed_delta_served.py
never sees a patch) where the remote serves the route, a todo (POST /usertodo) where it serves that alone, else a
transcript append. The notice is a completed card, not a needs-you one, on purpose: a needs-you card also flips the
session's needs-input state, which lands in the frame's remainder a cycle later, and on THIS board that remainder move
crosses as a whole frame (the size guard sends a change whole when its PATCH reaches 0.6 of the frame; a remainder move's
patch is the changed cards plus the whole remainder, and this lab board meets the condition at its composition, ledger rows
and scalars about 79 percent of an 18.5 KB frame in the round-1 drive's record, where the kernel's recorded live board, 660
cards with a 17 percent remainder in 5.76 MB, does not, so there the same flip is a patch: tests/test_view_deltas.py
CatchUpRoadsOfAWholeFrameClient), and that frame would catch an old bundle up and hide the freeze this lab is meant to show. The visible observable is the card on the hub's
feed page ([data-key="a:notice:..."]) or, for a transcript append, two: the appended pair's bar on the remote lane of
the hub's TIMELINE page (those corners open the timeline too and read the drawn bars off its SVG), and the text of api's
provisional row on the hub's Outline, which swaps from the seed's last prompt to the appended one. The Outline lists a
session through its goal tree or a provisional card, and a lab session with no judge has the card PERMANENTLY, not
never: the remote mints it for a live session whose latest held segment is a prompt the planner has not placed
(kernel.py _provisional_card, at both old vintages), and with no judge the placement never comes (an earlier round's
docstring had this inverted). The Waiting page receives no frame from an old remote at all and draws nothing for the
pair.

Two classes run with no knob (this checkout on both sides; the second strips the caps term from the dial in the page,
which the kernel reads as the empty set an older kernel would hold, so it is the checked-in stand-in for a
caps-ignoring remote). The rest boot another vintage from a checkout root named by an env knob and are skipped without
it (CI has no old checkouts, and no browser): ROMP_CORNER_OLD_REMOTE_ROOT (a kernel that ignores caps, honours delta=1
and serves /notice: upstream/main), ROMP_CORNER_V1_REMOTE_ROOT (the slot path without /notice or /usertodo, e.g.
2b9db2bee: the change is a transcript append and the patch to look for is the 60 s clock-only one),
ROMP_CORNER_V0_REMOTE_ROOT (before the delta protocol, e.g. 8a4d48f10: whole frames), ROMP_CORNER_OLD_HUB_ROOT (a hub
kernel and PREBUILT vscode-extension/dist from before PR 815: main). ROMP_CORNER_HUB_ROOT overrides the hub for every
class that names no hub of its own: pointed at a checkout of the PR before the receiver (7a7b31ed2) it is the
fails-before lever (the stand-in's card never shows and the Outline files delta-unapplied rows; the pre-T278c
corner's timeline lane freezes at the seed's six bars while the pre-delta corner's still moves on whole frames).
ROMP_CORNER_REPORT_DIR, when set, gets one JSON per class with everything recorded, for a written record.

This lab boots subprocess kernels and drives Chromium; it loads no romp code in-process, so it carries no in-process
state-isolation preamble and is not scanned by tests/test_state_isolation_order.py (as its two siblings). Synthetic
only: placeholder uuids, hostname TESTHOST, the notes-api demo's session names, invented card text.
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
import test_federated_dial_terms_served as _dial   # noqa: E402  the two-kernel boot (the module, not its class)

SID_R0 = "11111111-2222-4333-8444-000000000701"   # "api" on TESTHOST: the session the change is filed for
SID_R1 = "11111111-2222-4333-8444-000000000702"   # "worker" on TESTHOST
# six more sessions on TESTHOST (the notes-api demo's other names), so the remote's full frame is several times a one-card
# patch: the slot path's size guard (_DELTA_MAX_FRACTION, 0.6) sends a whole frame when the patch is not worth it, and
# eight sessions keep one notice card well under it (896 B against an 18.5 KB full frame in the recorded drives)
EXTRA = [("11111111-2222-4333-8444-0000000007%02d" % n, name, n)
         for n, name in ((3, "web"), (4, "tests"), (5, "docs"), (6, "deploy"), (7, "search"), (8, "index"))]
HOST = "TESTHOST"
WID = "hublab"
NOTICE_KEY = "corner"
NOTICE_TITLE = "the notes-api index rebuild finished on TESTHOST"
TODO_TEXT = "check the notes-api ranking weights before the index rebuild"
APPEND_PROMPT = "a later turn: did the notes-api index rebuild finish?"
APPEND_REPLY = "It finished; the stemmer table is cached now."
SEED_LAST_PROMPT = "turn %d: what changed in the notes-api search?" % (_dial.SEED_PAIRS - 1)   # the seed's last prompt (_dial._transcript): api's provisional row before the change
LANE = HOST + ":" + SID_R0        # api's lane id on the hub's timeline (federation prefixes id AND name)
LANE_LABEL = HOST + ":api"        # its label's text
PROV_SEL = '#fleet-list .fl-prov[data-sid="%s"] .fl-prov-text' % LANE   # api's provisional row on the hub's Outline (fleet.ts makeProvRow, under the prefixed sid)
TODOS_ON = json.dumps({"enabled": True, "gt": 1})
BAD_ROWS = (("outline", "delta-unapplied"), ("outline", "feedDelta-unapplied"), ("waiting", "feedDelta-unapplied"),
            ("feed", "feedDelta-unapplied"), ("federation", "feedDelta-nobase"))


def _state_root(lab, name):
    return os.path.join(lab, name, "xdg", "romp")


def _root_knob(name):
    v = (os.environ.get(name) or "").strip()
    return os.path.abspath(v) if v else None


def _serves(root, route):
    """Whether the kernel at `root` has `route` in its POST table (read from the source: the lab must know which change it can make)."""
    try:
        src = Path(root or ROOT, "kernel", "kernel.py").read_text(errors="replace")
    except OSError:
        return False
    return ('"%s"' % route) in src


def is_page_federation_row(r):
    """A hostconn row federation.ts filed about TESTHOST: the pages' own federation rows, the positive control for a
    negative read over the hub's client-diag (an absent or renamed file must not pass as "no bad row")."""
    return r.get("surface") == "federation" and r.get("what") == "hostconn" and (r.get("data") or {}).get("host") == HOST


def read_hub_diag_rows(lab):
    """The hub's client-diag rows, read once a page's federation row is in (a bounded retry: the pages post their rows
    after the driver's last snapshot), else whatever is there. Shared with tests/test_federated_bars_delta_served.py."""
    path = os.path.join(_state_root(lab, "hub"), "client-diag.jsonl")
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
        if any(is_page_federation_row(r) for r in rows):
            break
        time.sleep(0.3)
    return rows


# The Chromium driver: hook every socket the pages dial (window.__dials), the type of every frame a relay socket
# receives (window.__frames) and every needSlot / needFullFeed / ready the page sends on any socket, with the socket
# it left on (window.__sends); optionally strip the caps term from the relay dial (cfg.stripCaps); open the hub's
# pages (cfg.apps: Waiting, Outline, feed, and the timeline where the change is a transcript append, whose visible
# sides are a bar there and the Outline's provisional row text); wait for each relay socket to hold the remote's full
# frame (and the timeline to draw the seed's bars); make the change; wait for its visible effect; optionally wait for a
# slot patch (cfg.waitDeltaMs, the 60 s clock-only one on an idle old remote); report. The kernel-side observables (the
# hub's client-diag, the remote's /perf) are read from Python.
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
const out = { pages: {}, before: {}, changePosted: null, cardSeen: false, cardSeenMs: null, todoSeen: false, todoCardSeen: false, deltaSeenMs: null,
              barsBefore: null, barSeenMs: null, barsAfter: null, panelBarsAfter: null, pane: null,
              provBefore: null, provSeenMs: null, provAfter: null, died: null };
const hook = (o) => {
  window.__dials = []; window.__frames = []; window.__sends = []; const W = window.WebSocket;
  const strip = (u) => o.stripCaps && u.indexOf("/remote/") !== -1 ? u.replace(/([?&])caps=[^&]*&?/, (m, sep) => sep) .replace(/[?&]$/, "") : u;
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
          if (m && m.type !== "ka") {
            const f = { sock: idx, t: String(m.type), slot: m.slot ? String(m.slot) : "", len: String(ev.data).length, at: Date.now() };
            if (m.type === "feed" || m.type === "feedDelta") { f.asks = Array.isArray(m.asks) ? m.asks.length : null; f.buildId = m.buildId; }
            if (m.type === "feed") f.rest = JSON.stringify(Object.fromEntries(Object.entries(m).filter(([k]) => k !== "asks" && k !== "ledgers" && k !== "now" && k !== "buildId"))).length;
            if (m.type === "delta") { f.coll = Object.keys(m.coll || {}); f.restKeys = Object.keys(m.rest || {}); f.restAll = !!m.restAll; const set = ((m.coll || {}).turns || {}).set; f.setKeys = set ? Object.keys(set) : []; }
            if (m.type === "bars") f.lanes = Object.keys(m.turns || {}).length;
            window.__frames.push(f);
          }
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
  // the timeline page's door (tests/test_federated_bars_delta_served.py has the same two): the page's boot assigns
  // window.__rompConnectTimeline and calls it with its TimelinePanel, kept as window.__tlPanel; __barCount counts the
  // drawn bars on one lane from the SVG (the coloured rects in the plot group whose centre sits on the lane label's row)
  Object.defineProperty(window, "__rompConnectTimeline", { configurable: true, get() { return undefined; },
    set(fn) { Object.defineProperty(window, "__rompConnectTimeline", { configurable: true, writable: true, value: (p) => { window.__tlPanel = p; return fn(p); } }); } });
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
};
const pages = {};
const barCount = () => pages.timeline.evaluate((l) => window.__barCount(l), cfg.laneLabel);
// the Outline's provisional row for api (cfg.provSel): its text, or null when the page draws no such row
const provText = () => pages.fleet.evaluate((sel) => { const e = document.querySelector(sel); return e ? e.textContent : null; }, cfg.provSel);
const APPS = cfg.apps;   // the pages this corner opens: an old remote serves the feed payload to no app=waiting client (the pane is the fork's), so those corners open the Outline and the feed alone
const snap = async (page) => page.evaluate(() => ({ dials: (window.__dials || []).slice(), frames: (window.__frames || []).slice(), sends: (window.__sends || []).slice() }));
try {
  for (const app of APPS) {
    const page = await context.newPage();
    page.on("pageerror", () => {});
    await page.addInitScript(hook, { stripCaps: !!cfg.stripCaps });
    await page.goto(cfg.urls[app]);
    pages[app] = page;
  }
  for (const app of APPS) {
    await pages[app].waitForFunction(() => (window.__dials || []).some((u) => u.indexOf("/remote/TESTHOST/ws") !== -1), null, { timeout: 30000 });
    if (app === "timeline") {
      await pages.timeline.waitForFunction(() => (window.__frames || []).some((f) => f.t === "bars"), null, { timeout: 30000 });
      await pages.timeline.bringToFront();   // the pane defers its draw while its document is hidden (_hiddenForPaint)
      try { await pages.timeline.waitForFunction(([l, n]) => window.__barCount(l) === n, [cfg.laneLabel, cfg.seedBars], { timeout: 20000 }); } catch (e) {}
      out.barsBefore = await barCount();   // the door's positive control: the seed's bars drawn on the remote lane
    } else {
      await pages[app].waitForFunction(() => (window.__frames || []).some((f) => f.t === "feed"), null, { timeout: 30000 });
    }
  }
  // the change lands on a QUIET relay: the ready handshake's own frames (the caps ack, the re-based whole frame that
  // follows it on some apps) would otherwise carry the change to a page that decodes no patch and hide the freeze this
  // lab is meant to show. Quiet = no new frame on any relay socket for 2 s (the pusher's steady state), up to 15 s.
  for (let i = 0; i < 7; i++) {
    const n1 = {}; for (const app of APPS) n1[app] = (await snap(pages[app])).frames.length;
    await pages[APPS[0]].waitForTimeout(2000);
    let quiet = true; for (const app of APPS) if ((await snap(pages[app])).frames.length !== n1[app]) quiet = false;
    if (quiet) break;
  }
  out.before = {}; for (const app of APPS) out.before[app] = (await snap(pages[app])).frames.length;   // frames past this index came after the change
  const t0 = Date.now();
  if (cfg.change === "notice") {
    const r = await fetch(cfg.noticeUrl, { method: "POST", headers: { "Content-Type": "application/json" },
                                           body: JSON.stringify({ id: cfg.sid, key: cfg.noticeKey, title: cfg.noticeTitle, needsYou: false, producer: "lab" }) });
    out.changePosted = await r.json();
    const rev = ((out.changePosted || {}).notice || {}).rev;
    const sel = '[data-key="a:notice:' + cfg.sid + ':' + cfg.noticeKey + ':' + rev + '"]';
    try { await pages.feed.locator(sel).first().waitFor({ state: "attached", timeout: cfg.waitMs }); out.cardSeen = true; out.cardSeenMs = Date.now() - t0; } catch (e) {}
  } else if (cfg.change === "todo") {
    const r = await fetch(cfg.todoUrl, { method: "POST", headers: { "Content-Type": "application/json" },
                                         body: JSON.stringify({ id: cfg.sid, text: cfg.todoText }) });
    out.changePosted = await r.json();
    if (pages.waiting) { try { await pages.waiting.locator(".ut-text", { hasText: cfg.todoText }).first().waitFor({ timeout: cfg.waitMs }); out.todoSeen = true; } catch (e) {} }
    // the feed page's rolled-up user-todo card for the session (a:usertodo:<sid>), where the vintage mints one
    try { await pages.feed.locator('[data-key="a:usertodo:' + cfg.sid + '"]').first().waitFor({ state: "attached", timeout: pages.waiting ? 3000 : cfg.waitMs }); out.todoCardSeen = true; } catch (e) {}
  } else if (cfg.change === "transcript") {
    const nFleet = (await snap(pages.fleet)).frames.length;
    out.provBefore = await provText();   // the Outline's row for api before the change: the seed's last prompt
    fs.appendFileSync(cfg.transcript.path, cfg.transcript.text);
    out.changePosted = { ok: true, appended: cfg.transcript.text.length };
    if (pages.timeline) {   // one visible side: the appended pair's bar on the remote lane of the hub's timeline
      await pages.timeline.bringToFront();
      try { await pages.timeline.waitForFunction(([l, n]) => window.__barCount(l) === n, [cfg.laneLabel, cfg.seedBars + 1], { timeout: cfg.waitMs }); out.barSeenMs = Date.now() - t0; } catch (e) {}
    }
    // the other: the Outline's row text swaps to the appended prompt, waited on the text itself (never a fixed delay: the
    // feed frame carrying the change lags the bars frame, and which frame carries it varies by vintage and run)
    try { await pages.fleet.waitForFunction(([sel, t]) => { const e = document.querySelector(sel); return !!e && e.textContent === t; }, [cfg.provSel, cfg.appendPrompt], { timeout: cfg.waitMs }); out.provSeenMs = Date.now() - t0; } catch (e) {}
    try { await pages.fleet.waitForFunction((n) => (window.__frames || []).length > n, nFleet, { timeout: cfg.waitMs }); } catch (e) {}
  }
  if (cfg.waitDeltaMs) {
    try { await pages.fleet.waitForFunction((n) => (window.__frames || []).slice(n).some((f) => f.t === "delta"), out.before.fleet, { timeout: cfg.waitDeltaMs }); out.deltaSeenMs = Date.now() - t0; } catch (e) {}
  }
  await pages.fleet.waitForTimeout(1500);   // let the panes' rows land on the hub
  if (cfg.change === "transcript") out.provAfter = await provText();
  if (pages.timeline) {
    out.barsAfter = await barCount();
    out.panelBarsAfter = await pages.timeline.evaluate((l) => window.__panelCount(l), cfg.lane);
    out.pane = await pages.timeline.evaluate((l) => { const p = window.__tlPanel; if (!p) return null;
      return { now: p.data && p.data.now, winSec: p.winSec(), offSec: p.offSec(), bars: (p._turnsRaw()[l] || []).map((b) => [b.start, b.end]) }; }, cfg.lane);
  }
  for (const app of APPS) out.pages[app] = await snap(pages[app]);
} catch (e) {
  out.died = String(e).slice(0, 400);
  for (const app of Object.keys(pages)) { try { out.pages[app] = await snap(pages[app]); } catch (e2) {} }
}
console.log("RESULT:" + JSON.stringify(out));
await browser.close();
"""


class _Corner(unittest.TestCase):
    """One corner: the roots (None = this checkout), whether the page strips the caps term, the change, the waits."""
    maxDiff = None
    hub_root = None          # the hub kernel's checkout (bin/) and, when not None, its PREBUILT vscode-extension/dist
    remote_root = None       # the remote kernel's checkout (bin/)
    strip_caps = False
    change = "notice"        # "notice" | "todo" | "transcript"
    wait_ms = 20000
    wait_delta_ms = 0
    apps = ("waiting", "fleet", "feed")

    @classmethod
    def setUpClass(cls):
        if cls is _Corner:
            raise unittest.SkipTest("the base class")
        cls.procs = []
        try:
            cls._boot()
        except BaseException:
            cls.tearDownClass()
            raise

    @classmethod
    def _knobs(cls):
        """Subclasses resolve their roots here; a missing knob skips the class."""
        return None

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here), the served lab needs them")
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            raise unittest.SkipTest("no playwright browser on this box, the served lab needs one (CI installs none)")
        cls._knobs()
        if cls.hub_root is None:   # the fails-before lever, for every class that names no hub of its own
            cls.hub_root = _root_knob("ROMP_CORNER_HUB_ROOT")
        for root in (cls.hub_root, cls.remote_root):
            if root and not os.path.isfile(os.path.join(root, "bin", "romp-kernel")):
                raise unittest.SkipTest("no bin/romp-kernel under %s" % root)
        if cls.change == "notice" and not _serves(cls.remote_root, "/notice"):
            raise unittest.SkipTest("the remote kernel at %s serves no /notice: this corner's change needs one" % (cls.remote_root or ROOT))
        if cls.change == "todo" and not _serves(cls.remote_root, "/usertodo"):
            raise unittest.SkipTest("the remote kernel at %s serves no /usertodo" % (cls.remote_root or ROOT))
        cls.lab = tempfile.mkdtemp(prefix="federated-corner-")
        if cls.hub_root:
            src = os.path.join(cls.hub_root, "vscode-extension", "dist")
            if not os.path.isfile(os.path.join(src, "federation.js")):
                raise unittest.SkipTest("no prebuilt dist under %s (build the extension there first)" % cls.hub_root)
            lab_dist.copy_prebuilt(src, os.path.join(cls.lab, "dist"))
        else:
            lab_dist.copy_dist(os.path.join(cls.lab, "dist"))
        for name in ("testhost", "hub"):
            root = _state_root(cls.lab, name)
            os.makedirs(root, exist_ok=True)
            Path(root, "user-todos-enabled.json").write_text(TODOS_ON)
            Path(root, "update-mode.json").write_text(json.dumps({"mode": "off"}))   # a vintage without ROMP_UPDATE_CHECK reads the file
        cls.rport, cls.rtoken = _dial._free_port(), "testtok-remote-cn"
        cls.hport, cls.htoken = _dial._free_port(), "testtok-hub-cn"
        rp, cls.rlog = _dial._kernel(cls.lab, "testhost", cls.rport, cls.rtoken, [(SID_R0, "api", 1), (SID_R1, "worker", 2)] + EXTRA,
                                     bin_dir=os.path.join(cls.remote_root or ROOT, "bin"))
        cls.procs.append(rp)
        hp, cls.hlog = _dial._kernel(cls.lab, "hub", cls.hport, cls.htoken, [], bin_dir=os.path.join(cls.hub_root or ROOT, "bin"))
        cls.procs.append(hp)
        body = json.dumps({"host": HOST, "kernelPort": cls.rport, "busPort": _dial._free_port(), "token": cls.rtoken}).encode()
        req = urllib.request.Request("http://127.0.0.1:%d/checkin?token=%s" % (cls.hport, cls.htoken), data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            ans = json.loads(resp.read().decode())
        if not ans.get("ok"):
            raise unittest.SkipTest("the hub refused the check-in: %r" % ans)
        rows = []
        for _ in range(60):
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
        # the remote's build as the hub's /tunnels row names it after the drive (kernelSha, read by the hub's supervisor off
        # the peer's /version; "" when it never answered one): the pages' delta breadcrumbs carry it in their why
        cls.hub_row = cls._hub_tunnels_row()
        cls.remote_sha = (cls.hub_row or {}).get("kernelSha") or ""
        cls.remote_wire = cls._remote_wire_memos()
        cls.hub_diag_rows = cls._read_hub_diag_rows()
        cls._report()

    @classmethod
    def _transcript_append(cls):
        """One closed user/assistant pair for `api`, appended to its transcript on the remote (the change a kernel with
        neither /notice nor /usertodo can take), as _dial.change_pair mints it: fresh uuids chained to the seed's last
        row, the user row a minute ago and the reply 30 s later (a bar with a width; the pane culls a zero-width one).
        Its visible side is the bar on the hub's timeline, which the corners that open that page assert."""
        cwd = os.path.join(cls.lab, "testhost", "proj")
        proj = os.path.join(cls.lab, "testhost", "claude", "projects")
        cands = [p for p in Path(proj).rglob(SID_R0 + ".jsonl")]
        if not cands:
            raise unittest.SkipTest("no transcript for the api session under %s" % proj)
        return {"path": str(cands[0]), "text": _dial.change_pair(SID_R0, 1, cwd, APPEND_PROMPT, APPEND_REPLY)}

    @classmethod
    def _drive(cls):
        cfg = os.path.join(cls.lab, "cfg.json")
        conf = {"urls": {app: "http://127.0.0.1:%d/%s?wid=%s&token=%s" % (cls.hport, app, WID, cls.htoken) for app in cls.apps},
                "noticeUrl": "http://127.0.0.1:%d/notice?token=%s" % (cls.rport, cls.rtoken),
                "todoUrl": "http://127.0.0.1:%d/usertodo?token=%s" % (cls.rport, cls.rtoken),
                "sid": SID_R0, "noticeKey": NOTICE_KEY, "noticeTitle": NOTICE_TITLE, "todoText": TODO_TEXT,
                "change": cls.change, "stripCaps": cls.strip_caps, "waitMs": cls.wait_ms, "waitDeltaMs": cls.wait_delta_ms, "apps": list(cls.apps),
                "lane": LANE, "laneLabel": LANE_LABEL, "seedBars": _dial.SEED_PAIRS, "provSel": PROV_SEL, "appendPrompt": APPEND_PROMPT}
        if cls.change == "transcript":
            conf["transcript"] = cls._transcript_append()
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
    def _hub_tunnels_row(cls):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/tunnels?token=%s" % (cls.hport, cls.htoken), timeout=5) as r:
                rows = json.loads(r.read().decode()).get("tunnels") or []
        except Exception:
            return None
        return next((t for t in rows if t.get("host") == HOST), None)

    @classmethod
    def _remote_wire_memos(cls):
        """The remote's memos.wire counters (feed_slot_split counts slot-path feed sends) and, for the record, its send
        counters by kind and slot (sends.full/delta/deduped.feed: count and bytes), read once after the driver."""
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/perf?token=%s" % (cls.rport, cls.rtoken), timeout=5) as r:
                perf = json.loads(r.read().decode())
            cls.remote_sends = perf.get("sends") if isinstance(perf.get("sends"), dict) else {}
            return ((perf.get("memos") or {}).get("wire")) or {}
        except Exception as e:
            cls.remote_sends = {}
            return {"error": str(e)}

    @classmethod
    def _read_hub_diag_rows(cls):
        return read_hub_diag_rows(cls.lab)

    @staticmethod
    def _is_page_federation_row(r):
        return is_page_federation_row(r)

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
        rec = {"corner": cls.__name__, "hub_root": cls.hub_root, "remote_root": cls.remote_root, "strip_caps": cls.strip_caps, "remote_sha": cls.remote_sha,
               "change": cls.change, "driver_error": cls.driver_error, "result": cls.result, "remote_wire": cls.remote_wire,
               "remote_sends": getattr(cls, "remote_sends", {}),
               "hub_diag_by_kind": rows,
               "outline_delta_unapplied": [r.get("data") for r in cls.hub_diag_rows if (r.get("surface"), r.get("what")) == ("outline", "delta-unapplied")][:5]}
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

    def _page(self, app):
        self._driver_ran()
        rec = (self.result.get("pages") or {}).get(app)
        self.assertTrue(rec, "the %s page reported its dials, frames and sends" % app)
        return rec

    def _relay_dial(self, app):
        relay = [u for u in self._page(app)["dials"] if "/remote/TESTHOST/ws" in u]
        self.assertTrue(relay, "the hub's %s page dialed the remote's relay socket: %r" % (app, self._page(app)["dials"]))
        return relay[0]

    def _kinds(self, app):
        """The (type, slot) of every frame the app's relay sockets received, in order."""
        return [(f["t"], f["slot"]) for f in self._page(app)["frames"]]

    def _after_full(self, app):
        ks = self._kinds(app)
        self.assertIn(("feed", ""), ks, "the %s relay socket received the remote's full frame: %r" % (app, ks))
        return ks[ks.index(("feed", "")) + 1:]

    def _after_change(self, app):
        """The (type, slot) of the frames the app's relay sockets received AFTER the change was made (the driver records
        each page's frame count at the change, once the relay had gone quiet)."""
        self._driver_ran()
        n = int((self.result.get("before") or {}).get(app) or 0)
        return self._kinds(app)[n:]

    def _sends(self, app, sock, typ):
        return [s for s in self._page(app)["sends"] if s["sock"] == sock and s["type"] == typ]

    def _bad_rows(self):
        return [(r.get("surface"), r.get("what"), r.get("data")) for r in self.hub_diag_rows if (r.get("surface"), r.get("what")) in BAD_ROWS]

    def _unknown_slot_rows(self):
        return [r.get("data") for r in self.hub_diag_rows if r.get("surface") == "federation" and (r.get("data") or {}).get("ev") == "delta-unknown-slot"]

    def _unkeyed_base_rows(self):
        return [r.get("data") for r in self.hub_diag_rows if r.get("surface") == "federation" and (r.get("data") or {}).get("ev") == "delta-unkeyed-base"]

    def _assert_the_unkeyed_bars_base_is_said_once(self):
        """A remote whose whole bars frame the receiver cannot key (its judging a flat list: every kernel before T278c)
        seeds no base, and the first bars PATCH that then finds none is said exactly once: one hostconn row from the
        timeline page's conn (the one page that receives bars), naming the host, the slot, the collection and shape the
        table could not key, and the remote's build as the hub's /tunnels row names it, however many patches resynced
        and however many whole frames were refused (the seed's, the ready's re-base, the resync's answers, the idle
        slot's reposts). The seed itself files nothing (the pre-delta corner, which never patches, has no row). The feed
        frame of the same vintage keys asks as the table does, so no row names the feed."""
        self._control()
        self.assertTrue(self._sends("timeline", "relay", "needSlot"), "a bars patch resynced on the timeline relay socket: the row is that patch's")
        # the expected why is DERIVED from the hub's /tunnels row, so its build tag is guarded present: a row naming no
        # kernelSha would make the expectation tagless and let a tagless actual row pass for the wrong reason
        self.assertTrue(self.remote_sha, "the hub's /tunnels row names the remote's build (kernelSha), the tag the expected row is built from: %r" % (self.hub_row,))
        why = "bars judging dictlist:k is a list @" + self.remote_sha
        self.assertEqual(self._unkeyed_base_rows(), [{"host": HOST, "ev": "delta-unkeyed-base", "why": why}],
                         "the first bars patch onto the refused seed is said once, by the timeline page's conn, naming the remote's build "
                         "(the hub's row: %r); rows by kind: %r"
                         % (self.hub_row, sorted({(r.get("surface"), r.get("what"), (r.get("data") or {}).get("ev")) for r in self.hub_diag_rows}),))

    def _control(self):
        self._driver_ran()
        control = [r for r in self.hub_diag_rows if self._is_page_federation_row(r)]
        self.assertTrue(control, "the hub's client-diag carries the pages' federation rows about TESTHOST (the posting road is live); "
                                 "by (surface, what): %r" % (sorted({(r.get("surface"), r.get("what")) for r in self.hub_diag_rows}),))

    def _split(self):
        wire = self.remote_wire
        return wire.get("feed_slot_split") if isinstance(wire, dict) else None

    # ---- the assertions the decoded corners share ----
    def _assert_dials(self, caps):
        for app in self.apps:
            qs = parse_qs(urlsplit(self._relay_dial(app)).query)
            self.assertEqual(qs.get("app"), [app])
            self.assertEqual(qs.get("delta"), ["1"], "the page's delta term rides the %s relay dial (since 2026-09-15)" % app)
            self.assertEqual(qs.get("caps"), (["feedDelta"] if caps else None), "the %s relay dial's caps term: %r" % (app, qs))

    def _assert_change_posted(self):
        self._driver_ran()
        posted = self.result.get("changePosted") or {}
        self.assertTrue(posted.get("ok"), "the remote took the change: %r" % (posted,))

    def _assert_card_seen(self, seen):
        self._driver_ran()
        self.assertEqual(bool(self.result.get("cardSeen")), seen,
                         ("the notice card TESTHOST filed after the relay sockets held its full frame %s on the hub's feed page within %d ms "
                          "(frames on the feed relay: %r)") % ("shows" if seen else "never shows", self.wait_ms, self._kinds("feed")))

    def _assert_bar_drawn(self):
        """The visible side of a transcript append: the hub's timeline drew the seed's bars on the remote lane before the
        change and one more within the wait after it, and the panel's held lane counts the same."""
        self._assert_change_posted()
        n = _dial.SEED_PAIRS
        self.assertEqual(self.result.get("barsBefore"), n,
                         "the hub's timeline drew the seed's %d bars on the %s lane before the change (-1: no such lane label; 0: no bar "
                         "drawn on it): %r" % (n, LANE_LABEL, self.result.get("pane")))
        self.assertIsNotNone(self.result.get("barSeenMs"),
                             "the appended pair's bar was drawn on the %s lane within %d ms (count after the wait: %r, the panel's: %r; "
                             "frames on the timeline relay after the change: %r)" % (LANE_LABEL, self.wait_ms, self.result.get("barsAfter"),
                                                                                       self.result.get("panelBarsAfter"), self._after_change("timeline")))
        self.assertEqual(self.result.get("barsAfter"), n + 1, "the lane shows %d bars after the change" % (n + 1))
        self.assertEqual(self.result.get("panelBarsAfter"), n + 1, "and the panel's held lane counts %d" % (n + 1))

    def _assert_outline_row_swaps(self):
        """The other visible side of a transcript append, on the hub's OUTLINE: the remote mints a provisional card for a
        live session whose latest held segment is a prompt the planner has not placed (kernel.py _provisional_card, at
        both old vintages), and with no judge in the lab the placement never comes, so the row is permanent and its text
        is the session's latest prompt. The hub's Outline draws it as api's .fl-prov row under the prefixed sid (fleet.ts
        makeProvRow); the append swaps its text from the seed's last prompt to the appended one, carried by whatever the
        vintage sends for the change. At 2d that is a whole feed frame, which needs no decoder. At 2c the carrier varies
        run to run: the append's asks patch alone (one drive), or a whole frame from the guard (the append moved the
        remainder) and then a patch (another). Against a hub before the receiver (ROMP_CORNER_HUB_ROOT at 7a7b31ed2)
        the patch is dropped and the row keeps the seed's text in the first case, and the whole frame swaps it in the
        second, so this is an added observable of the feed half beside the frame assertions, asserted on the text after
        the settle and never on the carrier; the frame assertions and the timeline bar are the fails-before pins."""
        self._assert_change_posted()
        self.assertEqual(self.result.get("provBefore"), SEED_LAST_PROMPT,
                         "the hub's Outline drew api's provisional row with the seed's last prompt before the change (None: no such row under %r)" % (PROV_SEL,))
        self.assertIsNotNone(self.result.get("provSeenMs"),
                             "the row's text swapped to the appended prompt within %d ms (after the wait: %r; frames on the Outline relay after the change: %r)"
                             % (self.wait_ms, self.result.get("provAfter"), self._after_change("fleet")))
        self.assertEqual(self.result.get("provAfter"), APPEND_PROMPT, "and reads the appended prompt after the settle")

    def _assert_nothing_dropped(self):
        self._control()
        self.assertEqual(self._bad_rows(), [], "every frame the relay sockets received was applied by federation.ts; the panes never saw one raw")
        self.assertEqual(self._unknown_slot_rows(), [], "no patch named a slot this side does not decode")
        for app in self.apps:
            self.assertEqual(self._sends(app, "local", "needSlot"), [], "the %s page asked the LOCAL kernel for no slot: nothing fell through to a pane" % app)
            self.assertEqual(self._sends(app, "relay", "needFullFeed"), [], "…and asked the remote for no full feed: every delta found its base")


class CornerBothNew(_Corner):
    """Both new (this checkout on both sides): the remote honours the cap and serves feedDelta frames, applied per host.
    A user sees the remote host's rows move like the local host's; no diag row, no ask, feed_slot_split 0."""

    def test_dials_announce_caps(self):
        self._assert_dials(caps=True)

    def test_the_card_shows(self):
        self._assert_change_posted()
        self._assert_card_seen(True)

    def test_frames_after_the_full_are_feed_deltas(self):
        for app in self.apps:
            self._after_full(app)
            after = self._after_change(app)
            self.assertIn(("feedDelta", ""), after, "the %s relay socket received the change as a feedDelta: %r" % (app, self._kinds(app)))
            self.assertEqual([k for k in self._kinds(app) if k[0] == "delta"], [], "no slot patch on the %s relay socket, ever: %r" % (app, self._kinds(app)))
            self.assertEqual(self._sends(app, "relay", "needSlot"), [])

    def test_nothing_dropped_and_no_split_path(self):
        self._assert_nothing_dropped()
        self.assertEqual(self._split(), 0, "the remote never re-encoded through the slot path: %r" % (self.remote_wire,))


class CornerCapsIgnoredStandIn(_Corner):
    """New local, a remote that ignores the cap (the checked-in stand-in: this checkout's kernel with the caps term
    stripped from the dial by the page, which the accept reads as the empty set an older kernel holds). The remote
    serves the feed as {type:"delta", slot:"feed"} patches; the conn's receiver reassembles them. A user sees the rows
    move; the remote pays a re-encode per build (feed_slot_split climbs). Red before the receiver (a hub at
    7a7b31ed2, ROMP_CORNER_HUB_ROOT): the card never shows and the Outline files a delta-unapplied row per patch."""
    strip_caps = True

    def test_dials_carry_no_caps(self):
        self._assert_dials(caps=False)

    def test_the_card_shows(self):
        self._assert_change_posted()
        self._assert_card_seen(True)

    def test_frames_after_the_full_are_slot_patches(self):
        # every relay socket is on the slot path (no feedDelta anywhere), and the change crossed as a patch on the sockets
        # the pusher served it alone to; a socket served a cycle later can get the change and whatever moved since in one
        # frame, which the guard sends whole, so the patch is asserted across the sockets, not on each
        patched = []
        for app in self.apps:
            self._after_full(app)
            after = self._after_change(app)
            self.assertEqual([k for k in self._kinds(app) if k[0] == "feedDelta"], [], "no feedDelta on the %s relay socket (the cap was not read): %r" % (app, self._kinds(app)))
            self.assertTrue(after, "a frame past the change reached the %s relay socket: %r" % (app, self._kinds(app)))
            if ("delta", "feed") in after:
                patched.append(app)
        self.assertTrue(patched, "the change crossed as a feed slot patch on at least one relay socket; frames per page: %r"
                        % ({app: self._page(app)["frames"] for app in self.apps},))

    def test_nothing_dropped_and_the_split_path_ran(self):
        self._assert_nothing_dropped()
        for app in self.apps:
            self.assertEqual(self._sends(app, "relay", "needSlot"), [], "the %s page's receiver applied every patch: no resync asked of the remote" % app)
        self.assertGreater(self._split() or 0, 0, "the remote re-encoded through the slot path: %r" % (self.remote_wire,))


class CornerNewLocalOldRemote(CornerCapsIgnoredStandIn):
    """New local, a REAL old remote (ROMP_CORNER_OLD_REMOTE_ROOT: a kernel that ignores caps, honours delta=1 and serves
    /notice; upstream/main is one). The dial carries the cap (ignored) and delta=1; the rest is the stand-in's."""
    strip_caps = False
    apps = ("fleet", "feed")   # an old remote serves the feed payload to no app=waiting relay client (the Waiting pane is the fork's)

    @classmethod
    def _knobs(cls):
        cls.remote_root = _root_knob("ROMP_CORNER_OLD_REMOTE_ROOT")
        if not cls.remote_root:
            raise unittest.SkipTest("optional: ROMP_CORNER_OLD_REMOTE_ROOT unset: the old-remote corner needs a checkout of a caps-ignoring kernel")

    def test_dials_carry_no_caps(self):
        self._assert_dials(caps=True)   # announced, and ignored by the remote: the frames below say so

    def test_nothing_dropped_and_the_split_path_ran(self):
        self._assert_nothing_dropped()
        for app in self.apps:
            self.assertEqual(self._sends(app, "relay", "needSlot"), [])
        if self._split() is not None:   # a vintage without the fork's counter reports nothing here
            self.assertGreater(self._split(), 0, "the remote re-encoded through the slot path: %r" % (self.remote_wire,))


class CornerNewLocalV1Remote(_Corner):
    """New local, an old remote with the slot path and neither /notice nor /usertodo (ROMP_CORNER_V1_REMOTE_ROOT, e.g.
    2b9db2bee). The change is a transcript append. On the FEED it crosses as a slot patch (the pair filed under asks,
    in the recorded drive) or, when it moves the remainder instead, as a whole frame (the guard) followed by the 60 s
    clock-only patch an idle slot emits; either patch is reassembled without a row, and its visible side is api's
    provisional row on the hub's Outline, whose text swaps to the appended prompt (the row is permanent for a session
    with no judge: the module docstring). The other visible side is the hub's TIMELINE: the remote lane gains a bar.
    That vintage keys the bars frame's
    judging as a flat list the receiver cannot key (view-deltas.ts, its header), so the receiver seeds no base for it:
    each bars patch (the append's, then the idle slot's clock-only one a minute later) is answered by a needSlot on
    the relay socket, the receiver's own resync, and that kernel re-sends the whole bars frame, which is the repair;
    the bar shows through it. Nothing is filed for a resync as such (the whole frame it earns is the repair), and
    nothing for the refused seed as such (at the seed this vintage and a pre-delta one send the same frame); the first
    bars PATCH that finds no base because the seed was refused is said once (a hostconn row, ev delta-unkeyed-base, why
    the slot, the collection and shape the table could not key, and this remote's build as the hub's /tunnels row names
    it, from the timeline page's conn), the one row that names why that host's bars cross whole."""
    change = "transcript"
    wait_ms = 20000
    wait_delta_ms = 80000
    apps = ("fleet", "feed", "timeline")

    @classmethod
    def _knobs(cls):
        cls.remote_root = _root_knob("ROMP_CORNER_V1_REMOTE_ROOT")
        if not cls.remote_root:
            raise unittest.SkipTest("optional: ROMP_CORNER_V1_REMOTE_ROOT unset")

    def test_dials(self):
        self._assert_dials(caps=True)

    def test_a_feed_patch_arrived_and_was_reassembled(self):
        # the append's own patch where the vintage files the pair under asks (1087 B, coll asks, in the round-4 drive), else
        # the idle slot's clock-only one a minute later (110 B in rounds 2 and 3, when the append moved the remainder and
        # crossed whole); either is a real patch from a real pre-T278c kernel, reassembled with no row and nothing asked
        self._assert_change_posted()
        kinds = self._kinds("fleet")
        after = self._after_change("fleet")
        self.assertIn(("delta", "feed"), after, "the Outline's relay socket received a feed slot patch after the change (the append's, or the idle slot's clock-only one, within %d ms): %r" % (self.wait_delta_ms, kinds))
        self.assertEqual([k for k in kinds if k[0] == "feedDelta"], [], "and no feedDelta: %r" % (kinds,))
        self.assertIsNotNone(self.result.get("deltaSeenMs"))

    def test_the_timeline_shows_the_appended_bar(self):
        self._assert_bar_drawn()

    def test_the_outline_row_swaps_to_the_appended_prompt(self):
        self._assert_outline_row_swaps()

    def test_the_bars_cross_whole_after_the_receivers_resync(self):
        # that vintage's whole bars frame seeds no base (its judging is a flat list): every bars patch asks THAT kernel
        # for the whole slot on the relay socket, exactly once per patch, and the whole frame that answers is what the
        # lane is drawn from; the local kernel is asked for nothing
        kinds = self._kinds("timeline")
        after = self._after_change("timeline")
        self.assertIn(("bars", ""), kinds, "the timeline relay socket received the remote's whole bars frame: %r" % (kinds,))
        patches = [i for i, k in enumerate(after) if k == ("delta", "bars")]
        self.assertTrue(patches, "the append crossed as a bars slot patch on the timeline relay socket: %r" % (after,))
        self.assertTrue(any(k == ("bars", "") for k in after[patches[0] + 1:]),
                        "a whole bars frame followed the first patch (the resync's answer): %r" % (after,))
        asks = self._sends("timeline", "relay", "needSlot")
        self.assertEqual([a["slot"] for a in asks], ["bars"] * len([k for k in kinds if k == ("delta", "bars")]),
                         "one needSlot for the bars slot per patch, on the relay socket: asks %r, frames %r" % (asks, kinds))
        self.assertEqual(self._sends("timeline", "local", "needSlot"), [])

    def test_the_unkeyed_bars_base_is_said_once(self):
        self._assert_the_unkeyed_bars_base_is_said_once()

    def test_nothing_dropped(self):
        self._assert_nothing_dropped()
        for app in ("fleet", "feed"):
            self.assertEqual(self._sends(app, "relay", "needSlot"), [], "the %s page's receiver applied every feed patch" % app)


class CornerNewLocalV0Remote(_Corner):
    """New local, a remote from before the delta protocol (ROMP_CORNER_V0_REMOTE_ROOT, e.g. 8a4d48f10): whole frames
    only, feed and bars, applied by the unchanged arms with nothing asked and NO row: that vintage's bars frame keys
    judging as a flat list too, so the receiver refuses it as a base, but a pre-delta kernel sends no patch, so the
    refusal costs nothing and nothing names it (the row is the first patch's; a row at the seed would have named a
    remote behaving as designed). The wire pays a whole frame per change and per minute, the pre-delta cost. The change
    is a transcript append (rounds 2 and 3 filed
    a todo, whose visible side that vintage has none of: it serves the feed payload to no Waiting client and minted no
    rolled-up todo card on the feed page); its visible sides are the bar on the hub's timeline and the swap of api's
    provisional row on the Outline, both asserted (the frames are whole here, so the swap is an observable beside the
    frame assertion, not a fails-before pin of the receiver)."""
    change = "transcript"
    apps = ("fleet", "feed", "timeline")

    @classmethod
    def _knobs(cls):
        cls.remote_root = _root_knob("ROMP_CORNER_V0_REMOTE_ROOT")
        if not cls.remote_root:
            raise unittest.SkipTest("optional: ROMP_CORNER_V0_REMOTE_ROOT unset")

    def test_dials(self):
        self._assert_dials(caps=True)

    def test_the_outline_row_swaps_to_the_appended_prompt(self):
        self._assert_outline_row_swaps()

    def test_whole_frames_only(self):
        self._assert_change_posted()
        for app in ("fleet", "feed"):
            self._after_full(app)
            after = self._after_change(app)
            self.assertIn(("feed", ""), after, "a whole feed frame reached the %s relay socket after the change: %r" % (app, self._kinds(app)))
            self.assertEqual([k for k in self._kinds(app) if k[0] in ("delta", "feedDelta")], [], "never a patch or a feedDelta on the %s relay socket: %r" % (app, self._kinds(app)))
        kinds = self._kinds("timeline")
        self.assertIn(("bars", ""), self._after_change("timeline"), "a whole bars frame reached the timeline relay socket after the change: %r" % (kinds,))
        self.assertEqual([k for k in kinds if k[0] == "delta"], [], "never a patch on the timeline relay socket: %r" % (kinds,))

    def test_the_timeline_shows_the_appended_bar(self):
        self._assert_bar_drawn()

    def test_no_row_names_a_remote_that_never_patches(self):
        # the receiver refused this vintage's bars seed (its judging is a flat list) exactly as it refuses the pre-T278c
        # corner's, and no patch ever came, so no row: the refusal is said at the first patch, never at the seed
        self._control()
        self.assertEqual([k for k in self._kinds("timeline") if k[0] == "delta"], [], "no patch on the timeline relay socket")
        self.assertEqual(self._unkeyed_base_rows(), [], "no delta-unkeyed-base row for a remote that sends whole frames only; rows by kind: %r"
                         % (sorted({(r.get("surface"), r.get("what"), (r.get("data") or {}).get("ev")) for r in self.hub_diag_rows}),))

    def test_nothing_dropped(self):
        self._assert_nothing_dropped()
        for app in self.apps:
            self.assertEqual(self._sends(app, "relay", "needSlot"), [], "nothing asked of the remote on the %s relay socket: whole frames need no resync" % app)


class CornerOldLocal(_Corner):
    """OLD local (ROMP_CORNER_OLD_HUB_ROOT: a hub kernel and prebuilt bundle from before PR 815, main), a new remote
    (this checkout). The dial carries delta=1 and no caps, the remote serves the feed as slot patches, and the old
    bundle decodes none: a user sees the remote host's rows frozen where its first full frame put them, no toast, no
    banner; the Outline files a delta-unapplied row per patch and posts a needSlot to the LOCAL kernel (which
    resyncs its own slot, never the remote's), the feed and Waiting panes drop the patches silently. The old page moves
    only when the remote serves a change WHOLE. The rule is a ratio, never a category: an un-updated hub applies whole
    frames only, so it drops any change whose patch stays under 0.6 of the whole frame (the size guard, kernel.py
    _DELTA_MAX_FRACTION), and on the kernel's recorded shape (about 660 cards, asks 4.8 MB against 0.95 MB of everything
    else) that is nearly every change: a needs-you flip is a 0.34 MB patch there. The roads to a whole frame, measured
    against the encoder (review round 4 of PR 815 driving km._send_slot on a synthetic 8-session board, 2026-09-19; pinned
    in tests/test_view_deltas.py CatchUpRoadsOfAWholeFrameClient), are a relay redial (a fresh upstream socket is served
    whole once); the size guard, when the PATCH reaches 0.6 of the frame: for a remainder move the patch is the changed
    cards plus the whole remainder, which happens on this lab board at its composition (ledger rows and scalars about 79
    percent of an 18.5 KB frame in the round-1 drive's record, so a needs-you card's state flip a cycle later crosses
    whole here and the old page shows the card 1.8 s late instead of never) and not on the measured live board at 17
    percent of 5.76 MB, where a remainder move is a patch too; for a change confined to the cards the patch is the
    changed cards alone, which reaches 0.6 for a change touching most cards (20 of 30 on the class's 8-session board;
    about 72 percent on the recorded shape, derived from its figures) or for a shrink whose del list reaches 0.6 of
    what remains, which needs a light remainder (30 to 2 cards on one session crosses; 30 to 0 on eight sessions is a
    patch; on the recorded shape 660 dels against the 0.95 MB remainder are 0.05, so that road is closed there); and an
    encoder error. An unkeyable collection is never frozen at all (such a remote sends whole frames always). Every other
    change confined to the cards (a card appearing, leaving, moving column or changing text) is lost until reload on
    every board, and the busier the board, the less often an old page catches up. That is why the card is a completed
    one here: on this board a needs-you card's whole frame would hide the freeze. PR 815 changes no kernel, so it
    repairs this corner through the hub's bundle alone: the hub reloads its page onto the new bundle. A remote-side
    guard (whole feed frames to a relay socket that announces no cap; the module docstring says why it is not taken
    here) would also cover the old hub's feed during a mixed-build window, not its timeline. A dashboard served by a
    box that has not taken PR 815 is in this corner; whether it catches up is its board's ratio, and on the measured
    live board the guard never fires on a remainder move: the phone's 86 rows in 2.4 minutes, rev 1 to 86 monotone,
    were such a board, one that caught up not once in the window."""

    @classmethod
    def _knobs(cls):
        cls.hub_root = _root_knob("ROMP_CORNER_OLD_HUB_ROOT")
        if not cls.hub_root:
            raise unittest.SkipTest("optional: ROMP_CORNER_OLD_HUB_ROOT unset: the old-local corner needs a checkout of the bundle before PR 815, built")

    def test_dials_carry_no_caps(self):
        self._assert_dials(caps=False)

    def test_the_remote_serves_slot_patches(self):
        self._assert_change_posted()
        self._after_full("feed")
        after = self._after_change("feed")
        self.assertIn(("delta", "feed"), after, "the feed relay socket received the change as a slot patch: %r" % (self._kinds("feed"),))
        if self._split() is not None:
            self.assertGreater(self._split(), 0)

    def test_what_the_user_sees_is_a_frozen_remote(self):
        self._control()
        self._assert_card_seen(False)
        unapplied = [d for s, w, d in self._bad_rows() if (s, w) == ("outline", "delta-unapplied")]
        self.assertTrue(unapplied, "the old Outline filed a delta-unapplied row per dropped patch; rows by kind: %r"
                        % (sorted({(r.get("surface"), r.get("what")) for r in self.hub_diag_rows}),))
        self.assertTrue(self._sends("fleet", "local", "needSlot"), "…and posted its needSlot to the LOCAL kernel, which cannot repair a remote slot")
        for app in self.apps:
            self.assertEqual(self._sends(app, "relay", "needSlot"), [], "nothing asked of the remote: the old bundle has no host to route by")


class CornerBothOld(CornerOldLocal):
    """Both old (ROMP_CORNER_OLD_HUB_ROOT and ROMP_CORNER_OLD_REMOTE_ROOT): the same frozen remote by the same mechanism,
    since the old remote serves slot patches to a delta=1 dial whatever the caps term says."""

    apps = ("fleet", "feed")

    @classmethod
    def _knobs(cls):
        cls.hub_root = _root_knob("ROMP_CORNER_OLD_HUB_ROOT")
        cls.remote_root = _root_knob("ROMP_CORNER_OLD_REMOTE_ROOT")
        if not (cls.hub_root and cls.remote_root):
            raise unittest.SkipTest("optional: ROMP_CORNER_OLD_HUB_ROOT and ROMP_CORNER_OLD_REMOTE_ROOT both needed")


if __name__ == "__main__":
    unittest.main()
