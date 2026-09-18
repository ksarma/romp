"""A federated feed-riding pane receives a REMOTE host's feed as feedDelta frames and applies them (2026-09-18).
Two hermetic kernels on one box: a hub that owns no session and a checked-in TESTHOST that owns two ("api",
"worker"). The hub's Waiting-on-you page and its Outline page each dial TESTHOST's relay socket. Then a user
todo is filed on TESTHOST (POST /usertodo, the postal bus's door), which changes TESTHOST's feed after the
relay sockets hold its full frame, so the next frame each relay socket gets is a delta.

Before this change the relay dial announced no caps, so the remote kernel served its feed on the view-delta
slot path ({type:"delta", slot:"feed"}, re-encoding every card per build: memos.wire feed_slot_split), which
nothing in the hub's pages decodes: the shim reassembles view deltas on its LOCAL socket alone, and
federation.ts applied a feedDelta for the local host only. The remote's board froze on its first full frame,
the Outline filed a `delta-unapplied` row per dropped frame and posted a needSlot the LOCAL kernel could not
answer (86 rows in 2.4 minutes on the user's phone), and the Waiting pane dropped the same frames silently.
Now federation.ts announces caps=feedDelta on every remote dial (REMOTE_DIAL_CAPS) and applies a remote host's
feedDelta onto the raw frame it holds for that host.

Five observables, green with the change:
  1. each relay dial URL (window.__dials) carries caps=feedDelta;
  2. the Waiting pane shows the todo TESTHOST filed after its full frame (the delta applied and reached the pane);
  3. the frames each relay socket received after its full frame are feedDelta, none of them {type:"delta"};
  4. the HUB's client-diag.jsonl carries no `delta-unapplied` (outline), `feedDelta-unapplied` (outline, waiting)
     or `feedDelta-nobase` (federation) row;
  5. the REMOTE kernel's /perf memos.wire.feed_slot_split stays 0 (it never took the re-encoding split path).
Red at the base on 1, 3 and 5 (run 2026-09-18: the dial carried no caps, no feedDelta frame reached either relay
socket, feed_slot_split counted every feed send). 2 and 4 are green at the base in THIS lab and are the fix's
end-to-end confirmation rather than its failing-before test: the lab's board is two sessions and one todo, and
the kernel mints one usertodo card per session with every todo row in the frame's remainder, so the slot path's
delta for the change is nearly the whole frame and its size guard (_DELTA_MAX_FRACTION) sends a full frame the
pane applies. The phone's board is large enough for the same change to go as a delta the pane dropped; the
failing-before test for the apply path is the real FederationManager fed a remote full frame and a remote
delta in ui/webview/federation-remote-feed-delta.test.ts, which also runs the no-base case (a remote delta
with no full frame held asks THAT kernel for one on its own socket), unreachable from outside a live page.

This lab boots subprocess kernels and drives Chromium; it loads no romp code in-process, so it carries no
in-process state-isolation preamble and is not scanned by tests/test_state_isolation_order.py (the same as
tests/test_federated_dial_terms_served.py, whose kernel boot it reuses). Synthetic only: placeholder uuids,
hostname TESTHOST, the notes-api demo's session names, invented todo text.
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

SID_R0 = "11111111-2222-4333-8444-000000000701"   # "api" on TESTHOST: the session the todo is filed for
SID_R1 = "11111111-2222-4333-8444-000000000702"   # "worker" on TESTHOST
HOST = "TESTHOST"
WID = "hublab"
TODO_TEXT = "check the notes-api ranking weights before the index rebuild"
TODOS_ON = json.dumps({"enabled": True, "gt": 1})   # kernel.py USER_TODOS_SWITCH_FILE: off unless the file says so


def _state_root(lab, name):
    return os.path.join(lab, name, "xdg", "romp")


# The Chromium driver: hook every socket the pages dial (window.__dials) and, on a relay socket, the type of
# every frame it receives (window.__frames), open the hub's Waiting and Outline pages, wait for each relay
# socket to hold the remote's full frame, file a todo on the REMOTE kernel, and wait for the Waiting pane to
# show it. The kernel-side observables (the hub's client-diag, the remote's /perf) are read from Python.
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
const out = { pages: {}, todoPosted: null, todoSeen: false, died: null };
const hook = () => {
  window.__dials = []; window.__frames = []; const W = window.WebSocket;
  window.WebSocket = function (url, protos) {
    window.__dials.push(String(url));
    const w = protos === undefined ? new W(url) : new W(url, protos);
    if (String(url).indexOf("/remote/") !== -1) {
      w.addEventListener("message", (ev) => {
        try { const m = JSON.parse(ev.data); if (m && m.type !== "ka") window.__frames.push({ t: String(m.type), slot: m.slot ? String(m.slot) : "" }); } catch (e) {}
      });
    }
    return w;
  };
  window.WebSocket.prototype = W.prototype; window.WebSocket.CONNECTING = 0; window.WebSocket.OPEN = 1; window.WebSocket.CLOSING = 2; window.WebSocket.CLOSED = 3;
};
const pages = {};
try {
  for (const app of ["waiting", "fleet"]) {
    const page = await context.newPage();
    page.on("pageerror", () => {});
    await page.addInitScript(hook);
    await page.goto(cfg.urls[app]);
    pages[app] = page;
  }
  for (const app of ["waiting", "fleet"]) {
    // the FederationManager attaches the checked-in remote on load; wait for its relay socket, then for the remote's full frame on it
    await pages[app].waitForFunction(() => (window.__dials || []).some((u) => u.indexOf("/remote/TESTHOST/ws") !== -1), null, { timeout: 30000 });
    await pages[app].waitForFunction(() => (window.__frames || []).some((f) => f.t === "feed"), null, { timeout: 30000 });
  }
  // the board changes on the REMOTE after both relay sockets hold its full frame: the next frame each gets is a delta
  const r = await fetch(cfg.todoUrl, { method: "POST", headers: { "Content-Type": "application/json" },
                                       body: JSON.stringify({ id: cfg.sid, text: cfg.todoText }) });
  out.todoPosted = await r.json();
  try { await pages.waiting.locator(".ut-text", { hasText: cfg.todoText }).first().waitFor({ timeout: 20000 }); out.todoSeen = true; } catch (e) {}
  // the Outline's relay socket gets the same change; wait for a frame past its full (a delta of either protocol), then let the pane's rows land on the hub
  try { await pages.fleet.waitForFunction(() => (window.__frames || []).some((f) => f.t !== "feed" && f.t !== "caps"), null, { timeout: 20000 }); } catch (e) {}
  await pages.fleet.waitForTimeout(1500);
  for (const app of ["waiting", "fleet"]) {
    out.pages[app] = await pages[app].evaluate(() => ({ dials: (window.__dials || []).slice(), frames: (window.__frames || []).slice() }));
  }
} catch (e) {
  out.died = String(e).slice(0, 400);
  for (const app of Object.keys(pages)) {
    try { out.pages[app] = await pages[app].evaluate(() => ({ dials: (window.__dials || []).slice(), frames: (window.__frames || []).slice() })); } catch (e2) {}
  }
}
console.log("RESULT:" + JSON.stringify(out));
await browser.close();
"""


class FederatedFeedDelta(unittest.TestCase):
    """Two kernels (a hub and a checked-in TESTHOST), two pages, one driver run in setUpClass; each method asserts one observable."""
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
        cls.lab = tempfile.mkdtemp(prefix="federated-feed-delta-")
        lab_dist.copy_dist(os.path.join(cls.lab, "dist"))   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        # user todos are OFF unless the install's switch file says so: on for both kernels, before either boots (the
        # remote files the todo; the hub's Waiting pane reads its own kernel's switch as the pane's)
        for name in ("testhost", "hub"):
            root = _state_root(cls.lab, name)
            os.makedirs(root, exist_ok=True)
            Path(root, "user-todos-enabled.json").write_text(TODOS_ON)
        # the REMOTE owns both sessions; the HUB owns none and shows them through the relay
        cls.rport, cls.rtoken = _dial._free_port(), "testtok-remote-fd"
        cls.hport, cls.htoken = _dial._free_port(), "testtok-hub-fd"
        rp, cls.rlog = _dial._kernel(cls.lab, "testhost", cls.rport, cls.rtoken, [(SID_R0, "api", 1), (SID_R1, "worker", 2)])
        cls.procs.append(rp)
        hp, cls.hlog = _dial._kernel(cls.lab, "hub", cls.hport, cls.htoken, [])
        cls.procs.append(hp)
        body = json.dumps({"host": HOST, "kernelPort": cls.rport, "busPort": _dial._free_port(), "token": cls.rtoken}).encode()
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
        cls.remote_wire = cls._remote_wire_memos()
        cls.hub_diag_rows = cls._read_hub_diag_rows()

    @classmethod
    def _drive(cls):
        cfg = os.path.join(cls.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump({"urls": {app: "http://127.0.0.1:%d/%s?wid=%s&token=%s" % (cls.hport, app, WID, cls.htoken) for app in ("waiting", "fleet")},
                       "todoUrl": "http://127.0.0.1:%d/usertodo?token=%s" % (cls.rport, cls.rtoken),
                       "sid": SID_R0, "todoText": TODO_TEXT}, f)
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
        """The remote's memos.wire counters (/perf), read once after the driver: feed_slot_split counts feed sends
        that took the view-delta split path (a ?delta=1 feed client without FEED_DELTA_CAP)."""
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/perf?token=%s" % (cls.rport, cls.rtoken), timeout=5) as r:
                perf = json.loads(r.read().decode())
            return ((perf.get("memos") or {}).get("wire")) or {}
        except Exception as e:
            return {"error": str(e)}

    @classmethod
    def _read_hub_diag_rows(cls):
        """Every row of the HUB's client-diag.jsonl: the pages post their rows to the kernel they are served by."""
        path = os.path.join(_state_root(cls.lab, "hub"), "client-diag.jsonl")
        rows = []
        try:
            with open(path) as fh:
                for ln in fh:
                    try:
                        rows.append(json.loads(ln))
                    except ValueError:
                        continue
        except OSError:
            pass
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
        if self.result.get("died"):
            self.fail("the driver died: %s" % self.result["died"])

    def _page(self, app):
        self._driver_ran()
        rec = (self.result.get("pages") or {}).get(app)
        self.assertTrue(rec, "the %s page reported its dials and frames" % app)
        return rec

    def _relay_dial(self, app):
        relay = [u for u in self._page(app)["dials"] if "/remote/TESTHOST/ws" in u]
        self.assertTrue(relay, "the hub's %s page dialed the remote's relay socket: %r" % (app, self._page(app)["dials"]))
        return relay[0]

    def test_each_relay_dial_announces_feed_delta(self):
        for app in ("waiting", "fleet"):
            qs = parse_qs(urlsplit(self._relay_dial(app)).query)
            self.assertEqual(qs.get("app"), [app])
            self.assertEqual(qs.get("caps"), ["feedDelta"],
                             "the %s page's relay dial announces the feedDelta capability federation.ts decodes: %r" % (app, qs))
            self.assertEqual(qs.get("delta"), ["1"], "the page's own terms still ride, as before")

    def test_the_todo_was_filed_on_the_remote(self):
        self._driver_ran()
        posted = self.result.get("todoPosted") or {}
        self.assertTrue(posted.get("ok") and posted.get("todoId"), "TESTHOST filed the todo (its switch is on in this lab): %r" % (posted,))

    def test_the_waiting_pane_shows_the_todo_the_remote_filed_after_its_full_frame(self):
        self._driver_ran()
        self.assertTrue(self.result.get("todoSeen"),
                        "the hub's Waiting pane shows the todo TESTHOST filed after the relay socket held its full frame: the remote's "
                        "delta was applied and reached the pane (frames on the waiting relay: %r)" % (self._page("waiting")["frames"],))

    def test_the_remote_serves_the_relay_sockets_feed_deltas_never_slot_deltas(self):
        for app in ("waiting", "fleet"):
            frames = self._page(app)["frames"]
            kinds = [f["t"] for f in frames]
            self.assertIn("feed", kinds, "the %s relay socket received the remote's full frame: %r" % (app, kinds))
            self.assertIn("feedDelta", kinds, "…and, after the board changed, a feedDelta frame: %r" % (kinds,))
            self.assertEqual([f for f in frames if f["t"] == "delta"], [],
                             "no view-delta slot frame reached the %s relay socket (nothing on this side decodes one): %r" % (app, kinds))

    def test_the_hub_files_no_unapplied_or_nobase_row(self):
        self._driver_ran()
        bad = [r for r in self.hub_diag_rows
               if (r.get("surface"), r.get("what")) in (("outline", "delta-unapplied"), ("outline", "feedDelta-unapplied"),
                                                         ("waiting", "feedDelta-unapplied"), ("federation", "feedDelta-nobase"))]
        self.assertEqual(bad, [], "every frame the relay sockets received was applied by federation.ts; the panes never saw one raw")

    def test_the_remote_never_took_the_feed_slot_split_path(self):
        self._driver_ran()
        wire = self.remote_wire
        self.assertIn("feed_slot_split", wire, "the remote's /perf memos.wire counters: %r" % (wire,))
        self.assertEqual(wire["feed_slot_split"], 0,
                         "the relay clients announced FEED_DELTA_CAP, so the remote never re-encoded every card through the slot path: %r" % (wire,))


if __name__ == "__main__":
    unittest.main()
