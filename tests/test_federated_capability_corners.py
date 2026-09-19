"""The capability corners of the federated relay dial, driven for real (2026-09-19): what a hub's pages receive from a
remote kernel of each vintage, and what a user sees, with the hub's bundle new or old.

Since 8fe70da07 (2026-09-15) every relay dial carries the page's delta=1; since PR 815 it carries caps=feedDelta too
and federation.ts decodes whatever a remote sends: a remote that honours the cap sends {type:"feedDelta"} (applied per
host); one that ignores the cap but honours delta=1 sends {type:"delta", slot:"feed"} patches (reassembled per conn by
Conn.viewDeltas); one that ignores both sends whole {type:"feed"} frames (applied as before). An OLD hub bundle (main
before PR 815) dials delta=1 without caps and decodes no patch, so the same remote's rows freeze on its pages after
the first full frame: the Outline files a delta-unapplied row per dropped patch and posts a needSlot to the LOCAL
kernel, the feed and Waiting panes drop them silently. No kernel change repairs that corner; the hub's bundle does,
so the hub box updates, the page reloads, and no remote needs a change for either slot.

Each class is one corner: two hermetic kernels (a hub owning no session, a checked-in TESTHOST owning "api" and
"worker"), the hub's Waiting, Outline and feed pages in one Chromium, every socket's dial URL, inbound frame types
and outbound asks (needSlot, needFullFeed) recorded, then ONE change on the remote after every relay socket holds its
full frame. The change is a notice card (POST /notice, an asks-only change: the slot path's delta for it is one card
against the whole frame, under the size guard, so a caps-ignoring kernel emits a real patch; a todo changes the
frame's remainder and the guard sends a whole frame instead, which is why tests/test_federated_feed_delta_served.py
never sees a patch) where the remote serves the route, a todo (POST /usertodo) where it serves that alone, else a
transcript append. The notice is a completed card, not a needs-you one, on purpose: a needs-you card also flips the
session's needs-input state, which lands in the frame's remainder a cycle later as a whole frame, and that frame would
catch an old bundle up and hide the freeze this lab is meant to show. The visible observable is the card on the hub's
feed page ([data-key="a:notice:..."]) or the todo on its Waiting pane (or the feed page's rolled-up todo card).

Two classes run with no knob (this checkout on both sides; the second strips the caps term from the dial in the page,
which the kernel reads as the empty set an older kernel would hold, so it is the checked-in stand-in for a
caps-ignoring remote). The rest boot another vintage from a checkout root named by an env knob and are skipped without
it (CI has no old checkouts, and no browser): ROMP_CORNER_OLD_REMOTE_ROOT (a kernel that ignores caps, honours delta=1
and serves /notice: upstream/main), ROMP_CORNER_V1_REMOTE_ROOT (the slot path without /notice or /usertodo, e.g.
2b9db2bee: the change is a transcript append and the patch to look for is the 60 s clock-only one),
ROMP_CORNER_V0_REMOTE_ROOT (before the delta protocol, e.g. 8a4d48f10: whole frames), ROMP_CORNER_OLD_HUB_ROOT (a hub
kernel and PREBUILT vscode-extension/dist from before PR 815: main). ROMP_CORNER_HUB_ROOT overrides the hub for the
no-knob classes: pointed at a checkout of the PR before the receiver (7a7b31ed2) it is the stand-in's fails-before
(the card never shows, the Outline files delta-unapplied rows). ROMP_CORNER_REPORT_DIR, when set, gets one JSON per
class with everything recorded, for a written record.

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
import uuid
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
# patch: the slot path's size guard (_DELTA_MAX_FRACTION, 0.6) sends a whole frame when the patch is not worth it, and on
# a two-session board one notice card is
EXTRA = [("11111111-2222-4333-8444-0000000007%02d" % n, name, n)
         for n, name in ((3, "web"), (4, "tests"), (5, "docs"), (6, "deploy"), (7, "search"), (8, "index"))]
HOST = "TESTHOST"
WID = "hublab"
NOTICE_KEY = "corner"
NOTICE_TITLE = "the notes-api index rebuild finished on TESTHOST"
TODO_TEXT = "check the notes-api ranking weights before the index rebuild"
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


# The Chromium driver: hook every socket the pages dial (window.__dials), the type of every frame a relay socket
# receives (window.__frames) and every needSlot / needFullFeed / ready the page sends on any socket, with the socket
# it left on (window.__sends); optionally strip the caps term from the relay dial (cfg.stripCaps); open the hub's
# Waiting, Outline and feed pages; wait for each relay socket to hold the remote's full frame; make the change; wait
# for its visible effect; optionally wait for a slot patch (cfg.waitDeltaMs, the 60 s clock-only one on an idle old
# remote); report. The kernel-side observables (the hub's client-diag, the remote's /perf) are read from Python.
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
const out = { pages: {}, before: {}, changePosted: null, cardSeen: false, cardSeenMs: null, todoSeen: false, todoCardSeen: false, deltaSeenMs: null, died: null };
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
            if (m.type === "delta") { f.coll = Object.keys(m.coll || {}); f.restKeys = Object.keys(m.rest || {}); f.restAll = !!m.restAll; }
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
};
const pages = {};
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
    await pages[app].waitForFunction(() => (window.__frames || []).some((f) => f.t === "feed"), null, { timeout: 30000 });
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
    fs.appendFileSync(cfg.transcript.path, cfg.transcript.text);
    out.changePosted = { ok: true, appended: cfg.transcript.text.length };
    try { await pages.fleet.waitForFunction((n) => (window.__frames || []).length > n, (await snap(pages.fleet)).frames.length, { timeout: cfg.waitMs }); } catch (e) {}
  }
  if (cfg.waitDeltaMs) {
    try { await pages.fleet.waitForFunction((n) => (window.__frames || []).slice(n).some((f) => f.t === "delta"), out.before.fleet, { timeout: cfg.waitDeltaMs }); out.deltaSeenMs = Date.now() - t0; } catch (e) {}
  }
  await pages.fleet.waitForTimeout(1500);   // let the panes' rows land on the hub
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
                raise unittest.SkipTest("no prebuilt dist under %s (run node esbuild.js there first)" % cls.hub_root)
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
        cls.remote_wire = cls._remote_wire_memos()
        cls.hub_diag_rows = cls._read_hub_diag_rows()
        cls._report()

    @classmethod
    def _transcript_append(cls):
        """One closed user/assistant pair for `api`, appended to its transcript on the remote (the change a kernel with
        neither /notice nor /usertodo can take): fresh uuids, the clock now."""
        cwd = os.path.join(cls.lab, "testhost", "proj")
        proj = os.path.join(cls.lab, "testhost", "claude", "projects")
        cands = [p for p in Path(proj).rglob(SID_R0 + ".jsonl")]
        if not cands:
            raise unittest.SkipTest("no transcript for the api session under %s" % proj)
        u, a = str(uuid.uuid4()), str(uuid.uuid4())
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        rows = [{"type": "user", "uuid": u, "parentUuid": None, "sessionId": SID_R0, "cwd": cwd, "timestamp": stamp, "promptSource": "typed",
                 "message": {"role": "user", "content": "a later turn: did the notes-api index rebuild finish?"}},
                {"type": "assistant", "uuid": a, "parentUuid": u, "sessionId": SID_R0, "cwd": cwd, "timestamp": stamp,
                 "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                             "content": [{"type": "text", "text": "It finished; the stemmer table is cached now."}]}}]
        return {"path": str(cands[0]), "text": "".join(json.dumps(r) + "\n" for r in rows)}

    @classmethod
    def _drive(cls):
        cfg = os.path.join(cls.lab, "cfg.json")
        conf = {"urls": {app: "http://127.0.0.1:%d/%s?wid=%s&token=%s" % (cls.hport, app, WID, cls.htoken) for app in cls.apps},
                "noticeUrl": "http://127.0.0.1:%d/notice?token=%s" % (cls.rport, cls.rtoken),
                "todoUrl": "http://127.0.0.1:%d/usertodo?token=%s" % (cls.rport, cls.rtoken),
                "sid": SID_R0, "noticeKey": NOTICE_KEY, "noticeTitle": NOTICE_TITLE, "todoText": TODO_TEXT,
                "change": cls.change, "stripCaps": cls.strip_caps, "waitMs": cls.wait_ms, "waitDeltaMs": cls.wait_delta_ms, "apps": list(cls.apps)}
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
            if any(cls._is_page_federation_row(r) for r in rows):
                break
            time.sleep(0.3)
        return rows

    @staticmethod
    def _is_page_federation_row(r):
        return r.get("surface") == "federation" and r.get("what") == "hostconn" and (r.get("data") or {}).get("host") == HOST

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
        rec = {"corner": cls.__name__, "hub_root": cls.hub_root, "remote_root": cls.remote_root, "strip_caps": cls.strip_caps,
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

    @classmethod
    def _knobs(cls):
        cls.hub_root = _root_knob("ROMP_CORNER_HUB_ROOT")

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
            raise unittest.SkipTest("ROMP_CORNER_OLD_REMOTE_ROOT unset: the old-remote corner needs a checkout of a caps-ignoring kernel")

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
    2b9db2bee). The change is a transcript append, which lands in the remainder and crosses as a whole frame (the
    guard); the patch is the 60 s clock-only one an idle slot emits, reassembled without a row. A user sees the rows
    current; nothing is dropped."""
    change = "transcript"
    wait_ms = 15000
    wait_delta_ms = 80000
    apps = ("fleet", "feed")

    @classmethod
    def _knobs(cls):
        cls.remote_root = _root_knob("ROMP_CORNER_V1_REMOTE_ROOT")
        if not cls.remote_root:
            raise unittest.SkipTest("ROMP_CORNER_V1_REMOTE_ROOT unset")

    def test_dials(self):
        self._assert_dials(caps=True)

    def test_a_clock_patch_arrived_and_was_reassembled(self):
        self._assert_change_posted()
        kinds = self._kinds("fleet")
        after = self._after_change("fleet")
        self.assertIn(("delta", "feed"), after, "the Outline's relay socket received a feed slot patch after the change (the append's, or the idle slot's clock-only one, within %d ms): %r" % (self.wait_delta_ms, kinds))
        self.assertEqual([k for k in kinds if k[0] == "feedDelta"], [], "and no feedDelta: %r" % (kinds,))
        self.assertIsNotNone(self.result.get("deltaSeenMs"))

    def test_nothing_dropped(self):
        self._assert_nothing_dropped()
        for app in self.apps:
            self.assertEqual(self._sends(app, "relay", "needSlot"), [])


class CornerNewLocalV0Remote(_Corner):
    """New local, a remote from before the delta protocol (ROMP_CORNER_V0_REMOTE_ROOT, e.g. 8a4d48f10): whole frames
    only, applied as before; the change is a todo (that vintage serves /usertodo). A user sees the rows move; the wire
    pays a whole frame per change and per minute, the pre-delta cost."""
    change = "todo"
    apps = ("fleet", "feed")

    @classmethod
    def _knobs(cls):
        cls.remote_root = _root_knob("ROMP_CORNER_V0_REMOTE_ROOT")
        if not cls.remote_root:
            raise unittest.SkipTest("ROMP_CORNER_V0_REMOTE_ROOT unset")

    def test_dials(self):
        self._assert_dials(caps=True)

    def test_whole_frames_only_and_the_todo_shows(self):
        self._assert_change_posted()
        for app in self.apps:
            self._after_full(app)
            after = self._after_change(app)
            self.assertIn(("feed", ""), after, "a whole feed frame reached the %s relay socket after the change: %r" % (app, self._kinds(app)))
            self.assertEqual([k for k in self._kinds(app) if k[0] in ("delta", "feedDelta")], [], "never a patch or a feedDelta on the %s relay socket: %r" % (app, self._kinds(app)))
        # the visible side is recorded, not asserted: that vintage serves the feed payload to no Waiting client, and whether it
        # mints the feed page's rolled-up todo card is its own affair; the frames above are the corner's claim

    def test_nothing_dropped(self):
        self._assert_nothing_dropped()


class CornerOldLocal(_Corner):
    """OLD local (ROMP_CORNER_OLD_HUB_ROOT: a hub kernel and prebuilt bundle from before PR 815, main), a new remote
    (this checkout). The dial carries delta=1 and no caps, the remote serves the feed as slot patches, and the old
    bundle decodes none: a user sees the remote host's rows frozen where its first full frame put them, no toast, no
    banner; the Outline files a delta-unapplied row per patch and posts a needSlot to the LOCAL kernel (which
    resyncs its own slot, never the remote's), the feed and Waiting panes drop the patches silently. The remote's own
    whole-frame fallbacks (the size guard, a redial, a change that moves the remainder) catch the board up now and
    then, which is why the card is a completed one here (a needs-you card's state flip sends such a frame a cycle
    later and the old page shows the card 1.8 s late instead of never). No change on the remote repairs
    this corner: the hub reloads its page onto the new bundle. This is the production state of a dashboard served by
    a box that has not taken PR 815, and the record of the phone's 86 rows in 2.4 minutes."""

    @classmethod
    def _knobs(cls):
        cls.hub_root = _root_knob("ROMP_CORNER_OLD_HUB_ROOT")
        if not cls.hub_root:
            raise unittest.SkipTest("ROMP_CORNER_OLD_HUB_ROOT unset: the old-local corner needs a checkout of the bundle before PR 815, built")

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
            raise unittest.SkipTest("ROMP_CORNER_OLD_HUB_ROOT and ROMP_CORNER_OLD_REMOTE_ROOT both needed")


if __name__ == "__main__":
    unittest.main()
