#!/usr/bin/env python3
"""T215: a kernel restart between an attachment's ship and its ack must not wedge the upload.

The wedge (verified on main before the fix): file bytes ride the ws as base64 dropFile and
complete on a droppedPath ack sent back on the SAME socket. pendingShips is in-memory and
nothing on romp:wsup ever re-shipped or failed it — so a kernel restart in the ship→ack window
left the chip pulsing forever, and a send held by the ship gate ("Wait for the upload") waited
on an ack that could no longer arrive: message plus attachment parked with no error.

The fix, both faces:
  * same-page reconnect (the served dashboard): every pending entry retains its encoded payload
    and re-ships on romp:wsup — the exact kernel-is-back event, never a timer. The ack/nack
    echoes the client's shipId, so a duplicate ack from a re-ship race retires exactly the chip
    that asked, and a stray twin is DROPPED instead of attached to the active tab. Since the fold
    that brought the reload core (T265: a kernel-served page reloads itself when the kernel serving
    it restarts), the page also publishes a hold on that reload while any ship awaits its ack
    (ui/webview/reload-hold.ts, window.__rompReloadHold; the core's shipsHold defers and re-checks),
    so the heal runs first and the reload follows it. Without the hold the reload landed about 1.7 s
    after the relaunch and took the payload with it (the fork's 2026-09-08 fold). The notices raised
    when the LAST ship retires (a nack: the file was not saved, the held message not sent; the ack of
    a held send on another tab) would die with that reload, which follows within the core's 500 ms
    re-check, so the page snapshots the toasts on screen into the persisted state on the pre-reload
    hook and the fresh page shows them again once (render.ts persistNoticesForReload, reload-hold.ts).
  * reload (the VS Code pipe reloads its webview on kernel reconnect): the payload dies with
    the page, so the ship NAMES persist beside the drafts and the next load says LOUDLY what
    was lost — never a silent vanish.

Two guards here:
  * SourcePins — runs everywhere, CI included: the wiring above, pinned in the sources (the
    webview-side twins live in ui/webview/pending-attach.test.ts).
  * NackNoticeSurvivesReload: the notice's executed guard, the same choreography with the state
    dir's drops path made a regular file before the relaunch, so the re-ship is NACKed; the old
    page's nack toast is latched, the reload follows, and the fresh page must show the notice, once.
  * ServedWedge — the executed guard: boots the hermetic kernel, opens the real /chat page,
    SIGSTOPs the kernel so the dropFile is shipped on a live socket that will never answer,
    holds a send behind the ship gate, SIGKILLs and relaunches the kernel — and asserts the
    reconnect re-ships, the thumbnail lands, and the held send fires, and only THEN the page reloads
    itself onto the relaunched kernel's boot id, with no loss to announce. Plus the regression leg:
    a normal ship+send against the restarted kernel behaves exactly as before. Skips LOUDLY
    when the extension deps or a playwright browser are absent (CI installs no browsers).

All fixtures synthetic.
"""
import base64
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")

RENDER = open(os.path.join(ROOT, "ui", "webview", "render.ts")).read()
KERNEL_SRC = open(os.path.join(BIN, "romp-kernel")).read()

SID = "aaaaaaaa-1111-2222-3333-444444444444"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=")


class SourcePins(unittest.TestCase):
    def test_payload_retained_and_reshipped_on_the_reconnect_event(self):
        self.assertIn("interface PendingShip { name: string; shipId: string; b64?: string }", RENDER)
        self.assertIn("if (entry) entry.b64 = b64;", RENDER)
        # the listener grew a body (T246: the local active-tab re-arm rides the same open event); the re-ship
        # is still its first statement
        self.assertIn('window.addEventListener("romp:wsup", () => {\n  reshipPendingUploads();', RENDER)
        # …and the federated twin (review finding 2026-09-01): the relay's own (re)open re-ships THAT
        # host's entries — scoped by ack socket. The kernel-reported hostUp does NOT: it fires in the
        # tick federation re-dials the relay, before the socket is open (second review, same day)
        self.assertIn('window.addEventListener("romp:hostRelayUp", (e) => {', RENDER)
        self.assertNotIn("reshipPendingUploads(m.hosts", RENDER)

    def test_ack_echoes_shipid_and_a_stray_twin_is_dropped(self):
        self.assertIn('ack["shipId"] = str(msg["shipId"])', KERNEL_SRC)
        self.assertIn("if (ackShip && !shipOwner(ackShip)) return;", RENDER)

    def test_a_reload_loss_is_loud_never_a_silent_vanish(self):
        self.assertIn("shipsInFlight: [...pendingShips.values()].flat().map((p) => p.name)", RENDER)
        self.assertIn("still uploading when this page reloaded, so it was NOT attached", RENDER)

    def test_the_last_retirements_notice_rides_the_reload_that_follows_it(self):
        # the fork's 2026-09-08 fold, review F2: the toasts on screen are snapshotted on the CORE's pre-reload hook
        # (not on pagehide: a navigation of the user's own says nothing twice, ReloadLossToast) and replayed once at load
        self.assertIn("function persistForReload(): void { persistScrollForReload(); persistNoticesForReload(); }", RENDER)
        self.assertIn("(window as any).__rompPersistForReload = persistForReload;", RENDER)
        self.assertIn('window.addEventListener("pagehide", persistScrollForReload);', RENDER)
        self.assertIn('pendingNotices: liveNotices(document.getElementById("warn-toasts"))', RENDER)
        self.assertIn("const taken = takePendingNotices(vscodeApi?.getState?.());", RENDER)
        self.assertIn("for (const text of taken.notices) warnToast(text);", RENDER)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
import { spawn } from "node:child_process";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
const out = { wedge: {}, regression: {} };
const die = async (why) => {
  fs.writeSync(1, "RESULT:" + JSON.stringify({ ...out, died: why }) + "\n");
  await browser.close();
  process.exit(0);
};

// ---- wedge: SIGSTOP the kernel so the ship rides a live socket that will never answer ----
await page.goto(cfg.url);
await page.waitForSelector("#composer-input", { timeout: 20000 });
const tab = await page.waitForSelector("#tabs .tab, #tabs [data-sid]", { timeout: 20000 }).catch(() => null);
if (!tab) await die("no session tab — the lab seed never reached the chat payload");
await page.waitForTimeout(500);   // let the shim's ws settle onto the live kernel
process.kill(cfg.kernelPid, "SIGSTOP");
await page.setInputFiles("body > input[type=file]", cfg.file);
await page.waitForSelector(".composer-file-pending", { timeout: 10000 }).catch(() => {});
out.wedge.chipUpAfterShip = await page.locator(".composer-file-pending").count();
await page.fill("#composer-input", cfg.msg);
await page.click("#composer-send");
// the ship gate: hold the send on the upload, the event this bug starved forever
await page.waitForSelector(".confirm-btn", { timeout: 10000 }).catch(() => {});
const waitBtn = page.locator(".confirm-btn", { hasText: "Wait for the upload" });
out.wedge.gateOffered = await waitBtn.count();
if (out.wedge.gateOffered) await waitBtn.click();
out.wedge.inputHeld = await page.inputValue("#composer-input");
out.wedge.chipStillPendingHeld = await page.locator(".composer-file-pending").count();
// ---- the order pin (the fork's 2026-09-08 fold, T215 meets T265): the page heals, THEN the reload core reloads it.
// A marker names this document, and a latch inside it records the heal in sessionStorage (which survives the
// reload) the moment the strip and the composer show it, so the driver can read what the old page saw after that
// page is gone. The MutationObserver runs as a microtask, ahead of any navigation; the interval is the belt.
const bootBefore = await page.evaluate((msg) => {
  window.__probe = 1;
  sessionStorage.removeItem("probe:healedHere");
  const look = () => {
    if (sessionStorage.getItem("probe:healedHere")) return;
    const input = document.getElementById("composer-input");
    const pending = document.querySelectorAll(".composer-file-pending").length;
    if (pending === 0 && input && input.value === "")
      sessionStorage.setItem("probe:healedHere", JSON.stringify({
        hold: window.__rompReloadHold, waiting: window.__rompReload ? window.__rompReload.waiting : null,
        contentHasMsg: (document.getElementById("content")?.textContent || "").includes(msg) }));
  };
  new MutationObserver(look).observe(document.body, { childList: true, subtree: true, attributes: true, characterData: true });
  setInterval(look, 20);
  return window.__rompReload ? window.__rompReload.boot : null;
}, cfg.msg);
out.wedge.bootBefore = bootBefore;
out.wedge.holdWhileShipping = await page.evaluate(() => window.__rompReloadHold);
// ---- the restart: the old socket dies with the ack still owed; a fresh kernel takes the port ----
process.kill(cfg.kernelPid, "SIGKILL");
const k2 = spawn(cfg.relaunch.cmd, [], { env: cfg.relaunch.env, detached: true,
  stdio: ["ignore", fs.openSync(cfg.relaunch.log, "a"), fs.openSync(cfg.relaunch.log, "a")] });
k2.unref();   // the kernel outlives this driver — an un-unref'd child held node open past RESULT
fs.writeSync(1, "KPID:" + k2.pid + "\n");
// a poll that survives the reload: an evaluate that lands while the document is being replaced throws, and that
// is not an answer, so it asks again. Returns the predicate's (truthy) value, or false at the deadline.
const settle = async (fn, arg, ms) => {
  const t0 = Date.now();
  for (;;) {
    let v = false;
    try { v = await page.evaluate(fn, arg); } catch (e) { /* mid-navigation */ }
    if (v) return v;
    if (Date.now() - t0 > ms) return false;
    await new Promise((r) => setTimeout(r, 50));
  }
};
// today (pre-fix) this wait dies: the chip pulses forever and the held send never fires.
// with the fix: romp:wsup re-ships, the ack retires the chip, and fireHeldSend sends the message. The latch
// writes only while the marker page lives, so a record means THAT page healed, before any reload.
const rec = await settle(() => JSON.parse(sessionStorage.getItem("probe:healedHere") || "null"), null, 45000);
out.wedge.healedAfterRestart = !!rec;
out.wedge.healRecord = rec || null;
// ...then the reload core's turn (T265): the marker is gone and the page carries the relaunched kernel's boot id
out.wedge.reloadedAfterHeal = await settle(
  (boot) => window.__probe !== 1 && !!window.__rompReload && window.__rompReload.boot !== boot, bootBefore, 30000);
await page.waitForSelector("#composer-input", { timeout: 20000 }).catch(() => {});
out.wedge.bootAfter = await page.evaluate(() => window.__rompReload ? window.__rompReload.boot : null).catch(() => null);
out.wedge.pendingAfterRestart = await page.locator(".composer-file-pending").count();
out.wedge.inputAfterRestart = await page.inputValue("#composer-input");
// the fresh page draws the transcript from the kernel, which holds the send the ack released
out.wedge.contentHasMsg = await settle(
  (msg) => (document.getElementById("content")?.textContent || "").includes(msg), cfg.msg, 15000);
// every ship settled BEFORE the reload, so the reload has no loss to announce
out.wedge.lossToast = await page.evaluate(
  () => (document.getElementById("warn-toasts")?.textContent || "").includes("still uploading"));
if (cfg.shots) await page.screenshot({ path: cfg.shots + "-wedge.png" });

// ---- regression: a normal ship+send against the restarted kernel, untouched ----
await page.reload();
await page.waitForSelector("#composer-input", { timeout: 20000 });
await page.waitForTimeout(1000);
// the reload must NOT cry ship-loss: the wedge's ships all settled before it
out.regression.lossToast = await page.evaluate(
  () => (document.getElementById("warn-toasts")?.textContent || "").includes("still uploading"));
await page.setInputFiles("body > input[type=file]", cfg.file);
const acked = await page.waitForFunction(() =>
  document.querySelectorAll(".composer-file-pending").length === 0 &&
  document.querySelectorAll(".composer-file").length > 0, { timeout: 15000 })
  .then(() => true).catch(() => false);
out.regression.thumbnailLanded = acked;
await page.fill("#composer-input", cfg.msg2);
await page.click("#composer-send");
out.regression.gateOpened = await page.locator(".confirm-btn").count();   // no pending ships → no gate
const sent = await page.waitForFunction((msg) => {
  const input = document.getElementById("composer-input");
  return input && input.value === "" &&
         (document.getElementById("content")?.textContent || "").includes(msg);
}, cfg.msg2, { timeout: 15000 }).then(() => true).catch(() => false);
out.regression.sentClean = sent;
if (cfg.shots) await page.screenshot({ path: cfg.shots + "-regression.png" });

fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");   // sync: exit must not truncate it
await browser.close();
process.exit(0);
"""


class _ShipLab(unittest.TestCase):
    """Shared hermetic lab: one kernel, one seeded SDK session, the real /chat page. Subclasses
    carry the choreography; each gets its own kernel (setUpClass per class)."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here) — the served wedge needs them")
        cls.lab = tempfile.mkdtemp(prefix="ship-reship-")
        b = subprocess.run(["node", "esbuild.js"], cwd=EXT, capture_output=True, text=True)
        if b.returncode != 0:
            raise unittest.SkipTest("esbuild failed here: " + (b.stderr or b.stdout)[-200:])
        dist = os.path.join(cls.lab, "dist")
        shutil.copytree(os.path.join(EXT, "dist"), dist)
        cls.state = os.path.join(cls.lab, "xdg", "romp")
        cwd = os.path.join(cls.lab, "proj")
        os.makedirs(os.path.join(cls.state, "names"), exist_ok=True)
        os.makedirs(os.path.join(cls.state, "sdk"), exist_ok=True)
        os.makedirs(cwd, exist_ok=True)
        # one synthetic SDK session so the chat page has a tab and a composer to ship into
        Path(cls.state, "names", SID).write_text("web\t%s\t\t\n" % cwd)
        Path(cls.state, "sdk", SID + ".json").write_text(json.dumps(
            {"sid": SID, "name": "web", "cwd": cwd, "mode": "auto",
             "effort": "high", "lastSid": SID, "alive": True}))
        Path(cls.state, "usage.json").write_text(json.dumps(
            {"five_hour": {"pct": 100}, "seven_day": {"pct": 10}}))  # park sends: no CLI spawns in the lab
        claude = os.path.join(cls.lab, "claude")
        # the kernel finds a session's transcript under Claude's project dir: EVERY non-alphanumeric char of the
        # realpath becomes '-' (jd._proj_dir). A slashes-only munge missed the '_' pytest's temp root can carry,
        # so the kernel found no transcript and drew an API-error turn instead (the batch-only flake, 2026-09-08).
        proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
        os.makedirs(proj, exist_ok=True)
        # a CLOSED turn (user + replied assistant): an OPEN one would invite the boot
        # reconcile to resume it — this lab must never spawn a real CLI
        Path(proj, SID + ".jsonl").write_text(
            json.dumps({"type": "user", "uuid": "11111111-2222-3333-4444-555555555555",
                        "parentUuid": None, "timestamp": "2026-09-01T00:00:00.000Z",
                        "sessionId": SID,
                        "message": {"role": "user", "content": "hello there"}}) + "\n" +
            json.dumps({"type": "assistant", "uuid": "22222222-3333-4444-5555-666666666666",
                        "parentUuid": "11111111-2222-3333-4444-555555555555",
                        "timestamp": "2026-09-01T00:00:05.000Z", "sessionId": SID,
                        "message": {"role": "assistant", "model": "claude-sonnet-5",
                                    "content": [{"type": "text", "text": "hi from the lab"}],
                                    "stop_reason": "end_turn"}}) + "\n")
        cls.png = os.path.join(cls.lab, "shot.png")
        Path(cls.png).write_bytes(PNG)
        cls.port = _free_port()
        cls.token = "testtok-reship"
        cls.env = dict(os.environ,
                       XDG_STATE_HOME=os.path.join(cls.lab, "xdg"),
                       CLAUDE_CONFIG_DIR=claude,
                       ROMP_MANAGER_PORT="1", ROMP_KERNEL_NO_OPEN="1",
                       ROMP_SERVE_TOKEN=cls.token, ROMP_KERNEL_PORT=str(cls.port),
                       ROMP_DIST_DIR=dist,
                       ROMP_MODEL_CATALOG="off")   # hermetic: the T222 catalog fetch must never reach the network
        cls.env.pop("ROMP_STATE_DIR", None)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")],
                                      stdout=open(cls.klog, "w"), stderr=subprocess.STDOUT, env=cls.env)
        cls.kernel2_pid = None
        import urllib.request
        for _ in range(120):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/healthz" % cls.port, timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            cls.kernel.kill()
            raise unittest.SkipTest("hermetic kernel never served /healthz here")

    @classmethod
    def tearDownClass(cls):
        for pid in [getattr(cls, "kernel", None) and cls.kernel.pid, getattr(cls, "kernel2_pid", None)]:
            if pid:
                try:
                    os.kill(pid, signal.SIGCONT)   # a SIGSTOPped kernel ignores SIGTERM until resumed
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        if getattr(cls, "kernel", None):
            cls.kernel.wait()
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def _run_driver(self, driver_src, cfg_obj, timeout=300):
        cfg = os.path.join(self.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump(cfg_obj, f)
        driver = os.path.join(self.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(driver_src)
        try:
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=timeout,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        except subprocess.TimeoutExpired as e:
            so = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            se = (e.stderr or b"").decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            # the driver may have relaunched the lab kernel before hanging — reap it via tearDownClass
            # (review finding 2026-09-01: this path leaked the detached replacement kernel)
            kpid = next((ln for ln in so.splitlines() if ln.startswith("KPID:")), None)
            if kpid:
                type(self).kernel2_pid = int(kpid.split(":", 1)[1])
            self.fail("driver timed out; partial output:\n%s\n%s" % (so, se))
            return None
        kpid = next((ln for ln in p.stdout.splitlines() if ln.startswith("KPID:")), None)
        if kpid:
            type(self).kernel2_pid = int(kpid.split(":", 1)[1])
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box — the served leg needs one (CI installs none)")
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:])
        r = json.loads(line[len("RESULT:"):])
        self.assertNotIn("died", r, "driver aborted early: %r" % r)
        return r


class ServedWedge(_ShipLab):
    def test_restart_between_ship_and_ack_reships_heals_and_releases_the_held_send(self):
        r = self._run_driver(DRIVER, {
            "url": "http://127.0.0.1:%d/chat?token=%s" % (self.port, self.token),
            "kernelPid": self.kernel.pid,
            "relaunch": {"cmd": os.path.join(BIN, "romp-kernel"),
                         "env": {k: v for k, v in self.env.items()}, "log": self.klog},
            "file": self.png, "msg": "hold this message for the upload T215",
            "msg2": "a normal send after the restart T215",
            "shots": os.environ.get("SHIP_RESHIP_SHOTS", "")})
        w, reg = r["wedge"], r["regression"]
        # the ship went out on a live socket the stopped kernel will never answer
        self.assertEqual(w["chipUpAfterShip"], 1, "the pending chip must be up after the ship: %r" % w)
        self.assertEqual(w["gateOffered"], 1, "the ship gate must offer to wait for the upload: %r" % w)
        self.assertEqual(w["inputHeld"], "hold this message for the upload T215",
                         "the held send keeps the composer text until the upload settles: %r" % w)
        self.assertEqual(w["chipStillPendingHeld"], 1, "the chip is honestly pending while held: %r" % w)
        # the heart of T215: after the restart the reconnect re-ships, the ack lands, the send fires
        self.assertTrue(w["healedAfterRestart"],
                        "the reconnect must re-ship and release the held send — pre-fix this pulses "
                        "forever and the send never fires: %r (kernel log tail: %s)"
                        % (w, Path(self.klog).read_text()[-500:]))
        self.assertEqual(w["pendingAfterRestart"], 0, "no chip may pulse over an upload that settled: %r" % w)
        self.assertEqual(w["inputAfterRestart"], "", "the held send must have fired: %r" % w)
        self.assertTrue(w["contentHasMsg"], "the sent message must be in the transcript view: %r" % w)
        # ...and only THEN the reload core's reload (the fork's 2026-09-08 fold, T215 meets T265): the page held
        # the reload while the ship awaited its ack, the core deferred, and the fresh page has no loss to announce
        self.assertTrue(w["holdWhileShipping"],
                        "the page publishes window.__rompReloadHold while a ship awaits its ack: %r" % w)
        self.assertTrue(w["reloadedAfterHeal"],
                        "the reload core reloads once the ships settled (a new boot id, the marker gone): %r" % w)
        self.assertNotEqual(w["bootAfter"], w["bootBefore"], "the fresh page carries the relaunched kernel's boot id: %r" % w)
        self.assertFalse(w["lossToast"], "the reload came after the ack, so it has no loss to announce: %r" % w)
        # regression: the restarted kernel serves a NORMAL ship+send exactly as before
        self.assertFalse(reg["lossToast"], "a clean reload must not cry ship-loss: %r" % reg)
        self.assertTrue(reg["thumbnailLanded"], "normal ship: chip → thumbnail on the ack: %r" % reg)
        self.assertEqual(reg["gateOpened"], 0, "no pending ships → no gate: %r" % reg)
        self.assertTrue(reg["sentClean"], "a plain send still clears and lands: %r" % reg)


DRIVER_RELOAD = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
const out = {};
const die = async (why) => {
  fs.writeSync(1, "RESULT:" + JSON.stringify({ ...out, died: why }) + "\n");
  await browser.close();
  process.exit(0);
};
await page.goto(cfg.url);
await page.waitForSelector("#composer-input", { timeout: 20000 });
const tab = await page.waitForSelector("#tabs .tab, #tabs [data-sid]", { timeout: 20000 }).catch(() => null);
if (!tab) await die("no session tab — the lab seed never reached the chat payload");
await page.waitForTimeout(500);
// stop the kernel so the ship's ack cannot land, then WALK AWAY mid-flight: the loss shape.
// No restart needed — determinism comes from the page dying before any ack or re-ship can settle.
process.kill(cfg.kernelPid, "SIGSTOP");
await page.setInputFiles("body > input[type=file]", cfg.file);
await page.waitForSelector(".composer-file-pending", { timeout: 10000 }).catch(() => {});
out.chipUp = await page.locator(".composer-file-pending").count();
await page.goto("about:blank");            // the page dies with the ship pending — no client left to ack
process.kill(cfg.kernelPid, "SIGCONT");    // the buffered dropFile answers a dead socket, harmlessly
// load 1: the persisted names must warn LOUDLY — and clear
await page.goto(cfg.url);
await page.waitForSelector("#composer-input", { timeout: 20000 });
await page.waitForTimeout(800);
out.toastOnFirstLoad = await page.evaluate(
  () => (document.getElementById("warn-toasts")?.textContent || "").includes("still uploading"));
// load 2: silence — pre-fix, persistDrafts' swallowed TDZ throw left the record, re-toasting forever
await page.goto(cfg.url);
await page.waitForSelector("#composer-input", { timeout: 20000 });
await page.waitForTimeout(800);
out.toastOnSecondLoad = await page.evaluate(
  () => (document.getElementById("warn-toasts")?.textContent || "").includes("still uploading"));
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""


DRIVER_NACK = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
import { spawn } from "node:child_process";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
const out = {};
const die = async (why) => {
  fs.writeSync(1, "RESULT:" + JSON.stringify({ ...out, died: why }) + "\n");
  await browser.close();
  process.exit(0);
};
await page.goto(cfg.url);
await page.waitForSelector("#composer-input", { timeout: 20000 });
const tab = await page.waitForSelector("#tabs .tab, #tabs [data-sid]", { timeout: 20000 }).catch(() => null);
if (!tab) await die("no session tab: the lab seed never reached the chat payload");
await page.waitForTimeout(500);
// the same wedge as ServedWedge: a ship on a live socket the stopped kernel never answers, the send held on the gate
process.kill(cfg.kernelPid, "SIGSTOP");
await page.setInputFiles("body > input[type=file]", cfg.file);
await page.waitForSelector(".composer-file-pending", { timeout: 10000 }).catch(() => {});
out.chipUpAfterShip = await page.locator(".composer-file-pending").count();
await page.fill("#composer-input", cfg.msg);
await page.click("#composer-send");
await page.waitForSelector(".confirm-btn", { timeout: 10000 }).catch(() => {});
const waitBtn = page.locator(".confirm-btn", { hasText: "Wait for the upload" });
out.gateOffered = await waitBtn.count();
if (out.gateOffered) await waitBtn.click();
// the latch: this document records the nack toast the moment it appears (sessionStorage survives the reload)
const bootBefore = await page.evaluate(() => {
  window.__probe = 1;
  sessionStorage.removeItem("probe:nackSeen");
  const look = () => {
    if (sessionStorage.getItem("probe:nackSeen")) return;
    const toasts = document.getElementById("warn-toasts")?.textContent || "";
    if (toasts.includes("couldn't be saved"))
      sessionStorage.setItem("probe:nackSeen", JSON.stringify({ text: toasts, hold: window.__rompReloadHold,
        waiting: window.__rompReload ? window.__rompReload.waiting : null }));
  };
  new MutationObserver(look).observe(document.body, { childList: true, subtree: true, attributes: true, characterData: true });
  setInterval(look, 20);
  return window.__rompReload ? window.__rompReload.boot : null;
});
out.bootBefore = bootBefore;
// the drops path becomes a regular file: the relaunched kernel's _save_dropped_file fails and NACKs the re-ship
fs.rmSync(cfg.drops, { recursive: true, force: true });
fs.writeFileSync(cfg.drops, "not a directory");
process.kill(cfg.kernelPid, "SIGKILL");
const k2 = spawn(cfg.relaunch.cmd, [], { env: cfg.relaunch.env, detached: true,
  stdio: ["ignore", fs.openSync(cfg.relaunch.log, "a"), fs.openSync(cfg.relaunch.log, "a")] });
k2.unref();
fs.writeSync(1, "KPID:" + k2.pid + "\n");
const settle = async (fn, arg, ms) => {
  const t0 = Date.now();
  for (;;) {
    let v = false;
    try { v = await page.evaluate(fn, arg); } catch (e) { /* mid-navigation */ }
    if (v) return v;
    if (Date.now() - t0 > ms) return false;
    await new Promise((r) => setTimeout(r, 50));
  }
};
// the OLD page saw the nack (the re-ship failed to save), then the reload core's turn
out.nackSeen = await settle(() => JSON.parse(sessionStorage.getItem("probe:nackSeen") || "null"), null, 45000) || null;
out.reloaded = await settle(
  (boot) => window.__probe !== 1 && !!window.__rompReload && window.__rompReload.boot !== boot, bootBefore, 30000);
await page.waitForSelector("#composer-input", { timeout: 20000 }).catch(() => {});
out.bootAfter = await page.evaluate(() => window.__rompReload ? window.__rompReload.boot : null).catch(() => null);
// the FRESH page: the notice again (the replay is synchronous at load; the toast lives 12 s, so read it at once)
out.freshToasts = await settle(() => {
  const t = document.getElementById("warn-toasts")?.textContent || "";
  return t.includes("couldn't be saved") ? t : false;
}, null, 5000) || (await page.evaluate(() => document.getElementById("warn-toasts")?.textContent || "").catch(() => null));
// the draft comes back ONE time after load, once the tab has landed (restoreActiveDraftOnce): a poll, not a read
out.freshInput = await settle(() => document.getElementById("composer-input")?.value || false, null, 15000);
out.freshPending = await page.locator(".composer-file-pending").count();
out.freshFiles = await page.locator(".composer-file").count();
// one replay: the record is out of the persisted state as soon as the toasts are raised
out.recordAfterReplay = await page.evaluate(() => {
  const k = Object.keys(localStorage).find((x) => x.startsWith("romp-vscode-state-"));
  const st = k ? JSON.parse(localStorage.getItem(k) || "{}") : null;
  return st ? { hasKey: "pendingNotices" in st, notices: st.pendingNotices ?? null } : "no-state";
}).catch(() => null);
// dismissed, then a load the USER asks for: nothing to replay (the pagehide snapshot finds no toast on screen)
await page.keyboard.press("Escape");
out.toastsAfterEscape = await page.locator("#warn-toasts .warn-toast").count();
await page.goto(cfg.url);
await page.waitForSelector("#composer-input", { timeout: 20000 });
await page.waitForTimeout(800);
out.secondLoadToasts = await page.evaluate(() => document.getElementById("warn-toasts")?.textContent || "");
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""


class NackNoticeSurvivesReload(_ShipLab):
    """The fork's 2026-09-08 fold, review F2, executed: the reload core's restart reload follows the LAST pending
    ship's retirement within its 500 ms re-check, and the nack toast raised at that same moment (the file was not
    saved, the held message NOT sent) is DOM only: it died with the page, and the fresh page's loss toast had nothing
    to say (shipsInFlight was already empty), so a failed attachment and an unsent message went unannounced. The page
    now snapshots the toasts on screen into the persisted state on the pre-reload hook and the fresh page shows them
    again once. The drops path is made a regular file before the relaunch so the re-ship's save fails and the kernel
    NACKs it (_save_dropped_file); the old page's toast is latched in sessionStorage, which survives the reload."""

    def test_the_nack_of_the_last_ship_is_shown_again_by_the_fresh_page_once(self):
        r = self._run_driver(DRIVER_NACK, {
            "url": "http://127.0.0.1:%d/chat?token=%s" % (self.port, self.token),
            "kernelPid": self.kernel.pid,
            "relaunch": {"cmd": os.path.join(BIN, "romp-kernel"),
                         "env": {k: v for k, v in self.env.items()}, "log": self.klog},
            "file": self.png, "msg": "hold this message for the upload F2",
            "drops": os.path.join(self.state, "drops")})
        self.assertEqual(r["chipUpAfterShip"], 1, "the pending chip must be up after the ship: %r" % r)
        self.assertEqual(r["gateOffered"], 1, "the ship gate must offer to wait for the upload: %r" % r)
        # the old page: the re-ship was nacked, the toast named the file and the unsent message
        self.assertTrue(r["nackSeen"], "the relaunched kernel must NACK the re-ship (drops is a file): %r (kernel log tail: %s)"
                        % (r, Path(self.klog).read_text()[-500:]))
        self.assertIn("shot.png couldn't be saved", r["nackSeen"]["text"])
        self.assertIn("Your message was NOT sent", r["nackSeen"]["text"], "the held send did not fire without its file")
        # then the reload the core owed (held while the ship awaited its answer)
        self.assertTrue(r["reloaded"], "the reload core reloads once the ships settled: %r" % r)
        self.assertNotEqual(r["bootAfter"], r["bootBefore"], "the fresh page carries the relaunched kernel's boot id: %r" % r)
        # the heart of F2: the fresh page says it again, and the draft is still there to act on
        self.assertIn("shot.png couldn't be saved", r["freshToasts"] or "",
                      "the nack the reload wiped must be shown again by the fresh page: %r" % r)
        self.assertIn("Your message was NOT sent", r["freshToasts"] or "", "with the unsent message named: %r" % r)
        self.assertEqual(r["freshInput"], "hold this message for the upload F2", "the draft survives the reload as before: %r" % r)
        self.assertEqual([r["freshPending"], r["freshFiles"]], [0, 0], "no chip and no attachment over a file that was not saved: %r" % r)
        # once: the record is consumed by the replay, and a load after the toast is dismissed says nothing
        self.assertEqual(r["recordAfterReplay"], {"hasKey": False, "notices": None}, "the replay clears the record: %r" % r)
        self.assertEqual(r["toastsAfterEscape"], 0, "Escape dismisses the toasts: %r" % r)
        self.assertNotIn("couldn't be saved", r["secondLoadToasts"], "nothing on screen at the next navigation, nothing replayed: %r" % r)


class ReloadLossToast(_ShipLab):
    """The reload face, executed: a ship lost to a page death warns ONCE at the next load, then the
    record clears. Red on the pre-fix tree: the startup clear rode persistDrafts, whose stagedMsgs
    read sits below the restore block — the TDZ throw died in persistDrafts' own catch, the clear
    silently never ran, and the toast re-fired on every load (review finding 2026-09-01, verified
    on the emitted bundle)."""

    def test_reload_loss_toasts_once_then_clears(self):
        r = self._run_driver(DRIVER_RELOAD, {
            "url": "http://127.0.0.1:%d/chat?token=%s" % (self.port, self.token),
            "kernelPid": self.kernel.pid, "file": self.png})
        self.assertEqual(r["chipUp"], 1, "the ship must be pending when the page dies: %r" % r)
        self.assertTrue(r["toastOnFirstLoad"],
                        "the lost upload must warn loudly on the next load — never a silent vanish: %r" % r)
        self.assertFalse(r["toastOnSecondLoad"],
                         "the loss record must clear with the toast — one warning, not one per load: %r" % r)


if __name__ == "__main__":
    unittest.main()
