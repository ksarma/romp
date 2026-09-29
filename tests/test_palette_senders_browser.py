#!/usr/bin/env python3
"""The shell palette's two window listeners (ui/webview/palette-main.ts: openKeys, which opens the shortcuts dialog, and
hotkeyConfigure, which binds a tab's hot key) act only on a message from one of the shell's own panes, in real browsers.
Both read the shell's source check through ui/webview/pane-source.ts (paneSourceOk, fail-closed): a message counts only
when its immediate source is an iframe of the shell's document and its origin is the shell's location.origin.
ui/webview/foreign-sender-listeners.test.ts runs the two listeners over stand-ins; this lab runs the real shell page a
hermetic kernel serves, with its real bundles, and posts from every sender the gate must tell apart.

The three pane homes, each of which must reach the effect: the chat pane (#f-chat, posting to its parent as the tab
menu in render.ts does), a split chat column (#f-chat-2, opened by the shell's own split script through
__rompMoveTab, which render.ts's inRompShell sees as a pane of the shell) and the settings frame (#f-settings, whose
gear posts openKeys from its real shortcuts button; it posts no hotkeyConfigure). The six other senders, each of which
must reach nothing: the shell's own window (window.postMessage), the shell's own dispatch (a MessageEvent with no source
and no origin), a sourceless dispatch on the shell's location.origin, a same-origin frame nested in the chat pane
(top.postMessage), a same-origin tab the chat pane opened (opener.parent.postMessage) and a sandboxed frame nested in the
chat pane (origin "null"). A recorder the lab adds to the shell's window notes every such message as it arrives, with
its source (which of the shell's iframes, the shell itself, or none) and origin, so each refusal is read against a
message that reached the page, never against one that was not sent. The effect is read right after that delivery: the
shortcuts dialog open (both messages) and, for hotkeyConfigure, the session id the message named remembered in the tab
keys store (localStorage romp:tabkeys), which the palette writes before it opens the dialog on the hot key and forgets
when the dialog closes with no chord set.

Run in Chromium, Firefox and WebKit. Skips LOUDLY without the extension deps or a Playwright browser; under
ROMP_SERVED_TESTS_REQUIRE=1 (CI's served job) such a skip fails, except for an engine a runner that declares its engines
(ROMP_SERVED_TESTS_ENGINES) does not list, which stays an optional skip. PALETTE_SENDERS_DUMP=<dir> writes each engine's
record there. SYNTHETIC fixtures only: the notes-api demo's web and api sessions, placeholder ids."""
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
from datetime import datetime, timezone
from pathlib import Path

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment: a list of names, never a copy of the runner's

NAMES = ["web", "api"]
SIDS = {n: "%s-1111-2222-3333-444444444444" % (chr(ord("a") + i) * 8) for i, n in enumerate(NAMES)}
PALETTE = [("#9cd2ff", "#0c1a2e"), ("#1EA1EB", "#ffffff")]
PANE_HOMES = ["the chat pane (#f-chat)", "a split chat column (#f-chat-2)", "the settings frame's gear button (#f-settings)"]
OTHERS = ["the shell's own window", "the shell's own dispatch (no source, no origin)",
          "a sourceless dispatch on the shell's location.origin", "a same-origin frame nested in the chat pane",
          "a same-origin tab the chat pane opened", "a sandboxed frame nested in the chat pane"]


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const PW = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
const done = (o) => fs.writeFileSync(cfg.out, JSON.stringify(o));
let browser;
try { browser = await PW[cfg.engine].launch(); }
catch (e) { done({ skipped: String(e).slice(0, 400) }); process.exit(0); }
const out = { engine: cfg.engine, version: browser.version(), senders: [], pageErrors: [] };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function until(fn, ms) { const t0 = Date.now(); for (;;) { const v = await fn(); if (v) return v; if (Date.now() - t0 > ms) return v; await sleep(100); } }
try {
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 850 } });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => out.pageErrors.push(String(e).slice(0, 300)));
  await page.goto(cfg.url);
  await page.waitForSelector("#rail-gear", { timeout: 30000 });
  await until(() => page.evaluate(() => { const b = document.getElementById("romp-boot"); return !b || b.classList.contains("gone"); }), 15000);
  // the recorder: every openKeys or hotkeyConfigure message that reaches the shell's window, with its source and origin
  await page.evaluate(() => {
    window.__psr = [];
    window.addEventListener("message", (e) => {
      const d = e.data;
      if (!d || (d.romp !== "openKeys" && d.romp !== "hotkeyConfigure")) return;
      let frame = null;
      for (const f of document.querySelectorAll("iframe")) if (f.contentWindow === e.source) frame = f.id || f.className || "an iframe";
      window.__psr.push({ romp: d.romp, sid: typeof d.sid === "string" ? d.sid : "", self: e.source === window, sourceless: !e.source,
                          origin: e.origin, frame });
    }, true);
  });
  const keysOpen = () => page.evaluate(() => { const b = document.getElementById("rkeys-back"); return !!b && !b.hidden; });
  async function shut() { for (let i = 0; i < 5; i++) { if (!(await keysOpen())) return true; await page.evaluate(() => window.__rompKeysClose && window.__rompKeysClose()); await sleep(150); } return !(await keysOpen()); }
  const chatH = await page.waitForSelector("#f-chat", { state: "attached", timeout: 30000 });
  const chat = await chatH.contentFrame();
  await chat.waitForLoadState("load");
  await chat.waitForFunction((n) => document.querySelectorAll("#tabs .tab[data-id]").length >= n, cfg.count, { timeout: 30000 });
  // a split column, opened by the shell's own split script
  out.split = await page.evaluate((sid) => { const f = window.__rompMoveTab(sid, "new"); return f ? f.id : null; }, cfg.sidApi);
  const colH = await page.waitForSelector("#f-chat-2", { state: "attached", timeout: 30000 });
  const col = await colH.contentFrame();
  await col.waitForLoadState("load");
  out.colSrc = await colH.getAttribute("src");
  out.colInRompShell = await until(() => col.evaluate(() => { try { return parent !== window && !!parent.document.getElementById("chat-pane"); } catch (e) { return false; } }), 10000);
  const nested = (sandbox) => async (m) => chat.evaluate(([m, sandbox]) => new Promise((res) => {
    const tag = "ps-" + Math.random();
    window.addEventListener("message", (e) => { if (e.data && e.data.psSent === tag) res({ ran: true, origin: e.origin }); });
    const f = document.createElement("iframe");
    if (sandbox) f.setAttribute("sandbox", "allow-scripts");
    f.srcdoc = "<script>top.postMessage(" + JSON.stringify(m) + ",'*');parent.postMessage({psSent:" + JSON.stringify(tag) + "},'*');<\/script>";
    document.body.appendChild(f);
    setTimeout(() => res({ ran: false }), 8000);
  }), [m, sandbox]);
  let tab = null;
  const SENDERS = {
    "the chat pane (#f-chat)": async (m) => { await chat.evaluate((m) => parent.postMessage(m, "*"), m); return {}; },
    "a split chat column (#f-chat-2)": async (m) => { await col.evaluate((m) => parent.postMessage(m, "*"), m); return {}; },
    "the settings frame's gear button (#f-settings)": async () => {
      await page.click("#rail-gear");
      await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });
      const sh = await page.waitForSelector("#f-settings", { state: "attached", timeout: 20000 });
      const st = await sh.contentFrame();
      await st.waitForSelector("#rsettings:not([hidden])", { timeout: 20000 });
      const shown = await st.evaluate(() => { const r = document.getElementById("rs-keys-web"); return !!r && !r.hidden; });
      await st.evaluate(() => document.getElementById("rs-keys-btn").click());
      return { buttonShown: shown };
    },
    "the shell's own window": async (m) => { await page.evaluate((m) => window.postMessage(m, "*"), m); return {}; },
    "the shell's own dispatch (no source, no origin)": async (m) => { await page.evaluate((m) => window.dispatchEvent(new MessageEvent("message", { data: m })), m); return {}; },
    "a sourceless dispatch on the shell's location.origin": async (m) => {
      await page.evaluate((m) => window.dispatchEvent(new MessageEvent("message", { data: m, origin: location.origin })), m); return {}; },
    "a same-origin frame nested in the chat pane": nested(false),
    "a same-origin tab the chat pane opened": async (m) => {
      if (!tab) {
        const opened = ctx.waitForEvent("page", { timeout: 15000 }).catch(() => null);
        await chat.evaluate(() => { window.open("/chat?ps=1", "_blank"); });
        tab = await opened;
        if (tab) { try { await tab.waitForLoadState("load", { timeout: 20000 }); } catch (e) { /* read below */ } }
      }
      if (!tab) return { posted: "no tab opened" };
      return { posted: await tab.evaluate((m) => { try { opener.parent.postMessage(m, "*"); return "posted"; } catch (e) { return "threw " + e; } }, m) };
    },
    "a sandboxed frame nested in the chat pane": nested(true),
  };
  let n = 0;
  for (const label of cfg.senders) {
    for (const kind of ["openKeys", "hotkeyConfigure"]) {
      if (label.startsWith("the settings frame") && kind !== "openKeys") continue;   // the gear posts openKeys only
      n++;
      const sid = "11111111-2222-3333-4444-" + String(n).padStart(12, "0");
      const m = kind === "openKeys" ? { romp: "openKeys" } : { romp: "hotkeyConfigure", sid, name: "web" };
      const closedBefore = await shut();
      await page.evaluate(() => { window.__psr = []; });
      const extra = await SENDERS[label](m);
      const rec = await until(() => page.evaluate((k) => window.__psr.filter((r) => r.romp === k), kind).then((a) => (a.length ? a : null)), 10000) || [];
      await sleep(400);   // the palette's listener ran in the same dispatch as the recorder; the pause covers a paint
      const opened = await keysOpen();
      const tabKey = await page.evaluate((sid) => { try { return JSON.parse(localStorage.getItem("romp:tabkeys") || "{}")[sid] || null; } catch (e) { return "unreadable"; } }, sid);
      out.senders.push({ label, kind, sid: kind === "openKeys" ? "" : sid, closedBefore, recorded: rec, opened, tabKey, extra });
      await shut();
    }
  }
  if (tab) await tab.close();
} catch (e) {
  out.error = String((e && e.stack) || e).slice(0, 3000);
}
done(out);
await browser.close();
process.exit(0);
"""


class PaletteSendersInBrowsers(unittest.TestCase):
    maxDiff = None
    results = {}

    @classmethod
    def setUpClass(cls):
        try:
            cls._boot()
        except BaseException:
            cls.tearDownClass()
            raise

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served guard needs them")
        cls.lab = tempfile.mkdtemp(prefix="palette-senders-")
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        state = os.path.join(cls.lab, "xdg", "romp")
        claude = os.path.join(cls.lab, "claude")
        cwd = os.path.join(cls.lab, "proj")
        home = os.path.join(cls.lab, "home")
        for d in ("names", "sdk", "states"):
            os.makedirs(os.path.join(state, d), exist_ok=True)
        Path(state, "session-hosts").write_text("off\n")   # this lab mints its own state root: no session host (repo rule)
        os.makedirs(cwd, exist_ok=True)
        os.makedirs(home, exist_ok=True)
        proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
        os.makedirs(proj, exist_ok=True)
        t0 = int(time.time()) - 900
        for i, name in enumerate(NAMES):
            sid = SIDS[name]
            bg, fg = PALETTE[i % len(PALETTE)]
            Path(state, "names", sid).write_text("%s\t%s\t%s\t%s\n" % (name, cwd, bg, fg))
            Path(state, "sdk", sid + ".json").write_text(json.dumps(
                {"sid": sid, "name": name, "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": sid, "alive": True,
                 "model": "claude-opus-5", "liveModel": "Opus 5"}))
            recs = [{"type": "user", "timestamp": iso(t0 + i), "uuid": "u1", "parentUuid": None, "promptSource": "typed", "sessionId": sid,
                     "message": {"role": "user", "content": "what does the %s session do in notes-api?" % name}},
                    {"type": "assistant", "timestamp": iso(t0 + i + 5), "uuid": "a1", "parentUuid": "u1", "sessionId": sid,
                     "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                                 "content": [{"type": "text", "text": "It keeps the %s side of the notes-api tidy." % name}]}}]
            Path(proj, sid + ".jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
        Path(state, "usage.json").write_text(json.dumps({"five_hour": {"pct": 10}, "seven_day": {"pct": 10}}))
        cls.port, cls.token = _free_port(), "testtok-palette-senders"
        env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token, ROMP_HOST_NAME="TESTHOST", HOME=home)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"), stderr=subprocess.STDOUT, env=env)
        for _ in range(120):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/healthz" % cls.port, timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise AssertionError("the hermetic kernel never served /healthz:\n" + open(cls.klog).read()[-2000:])

    @classmethod
    def tearDownClass(cls):
        k = getattr(cls, "kernel", None)
        if k:
            k.terminate()
            try:
                k.wait(timeout=10)
            except subprocess.TimeoutExpired:
                k.kill()
                k.wait()
        lab = getattr(cls, "lab", "")
        if lab:
            shutil.rmtree(lab, ignore_errors=True)

    def _drive(self, engine):
        if engine in self.results:
            return self.results[engine]
        cfg = os.path.join(self.lab, "cfg-%s.json" % engine)
        out = os.path.join(self.lab, "result-%s.json" % engine)
        with open(cfg, "w") as f:
            json.dump({"url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token), "engine": engine, "out": out,
                       "count": len(NAMES), "sidApi": SIDS["api"], "senders": PANE_HOMES + OTHERS}, f)
        driver = os.path.join(self.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=420,
                           env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        if p.returncode != 0 or not os.path.exists(out):
            raise AssertionError("the %s driver failed (rc %d):\n%s%s\nkernel:\n%s" % (engine, p.returncode, p.stdout[-3000:],
                                 p.stderr[-3000:], open(self.klog).read()[-1500:]))
        o = json.loads(Path(out).read_text())
        if o.get("skipped"):
            declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
            if declared and engine not in [e.strip() for e in declared.split(",")]:
                # a runner that says which engines it installed (CI's served job: chromium) leaves the other legs as skips
                # even under ROMP_SERVED_TESTS_REQUIRE=1, which honours this prefix (tests/conftest.py)
                self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s): %s" % (engine, declared, o["skipped"]))
            self.skipTest("no playwright %s on this machine; this leg needs it (CI installs chromium): %s" % (engine, o["skipped"]))
        if o.get("error"):
            raise AssertionError("the %s driver threw: %s\n  so far: %s\nkernel:\n%s" % (engine, o["error"], json.dumps(o.get("senders"))[:3000],
                                 open(self.klog).read()[-1500:]))
        self.results[engine] = o
        if os.environ.get("PALETTE_SENDERS_DUMP"):   # a directory: each engine's record, for a reader of the run
            Path(os.environ["PALETTE_SENDERS_DUMP"], engine + ".json").write_text(json.dumps(o, indent=1) + "\n")
        return o

    def _check(self, engine):
        o = self._drive(engine)
        where = engine + " " + o.get("version", "") + ": "
        self.assertEqual(o["split"], "f-chat-2", where + "the shell's split script opened a second column")
        self.assertTrue(o["colSrc"].startswith("/chat?col=2"), where + "the column is the split script's chat page: " + str(o["colSrc"]))
        self.assertIs(o["colInRompShell"], True, where + "the column's page sees itself as a pane of the shell (render.ts inRompShell)")
        rows = {(r["label"], r["kind"]): r for r in o["senders"]}
        expected = [(label, kind) for label in PANE_HOMES + OTHERS for kind in ("openKeys", "hotkeyConfigure")
                    if not (label.startswith("the settings frame") and kind != "openKeys")]
        self.assertEqual(sorted(rows), sorted(expected), where + "every sender posted each message it has")
        frames = {"the chat pane (#f-chat)": "f-chat", "a split chat column (#f-chat-2)": "f-chat-2",
                  "the settings frame's gear button (#f-settings)": "f-settings"}
        for (label, kind), r in sorted(rows.items()):
            row = where + label + ", " + kind + ": " + json.dumps(r)[:900]
            self.assertTrue(r["closedBefore"], row + "\n  the dialog was closed before the post")
            rec = r["recorded"]
            self.assertEqual(len(rec), 1, row + "\n  the message reached the shell's window once (the recorder saw it)")
            rec = rec[0]
            if kind == "hotkeyConfigure":
                self.assertEqual(rec["sid"], r["sid"], row + "\n  the recorded message is this post's")
            if label in frames:
                self.assertEqual(rec["frame"], frames[label], row + "\n  its source is that iframe of the shell's document")
                self.assertTrue(rec["origin"].startswith("http://127.0.0.1:"), row + "\n  on the shell's location.origin")
                self.assertIs(r["opened"], True, row + "\n  a pane of the shell reaches the effect: the shortcuts dialog opens")
                if kind == "hotkeyConfigure":
                    self.assertEqual(r["tabKey"], "web", row + "\n  and the session the message named joins the tab keys store")
                if label.startswith("the settings frame"):
                    self.assertIs(r["extra"].get("buttonShown"), True, row + "\n  the gear showed its shortcuts button")
                continue
            # the senders that are no pane of the shell: the message arrived, and nothing acted on it
            if label == "the shell's own window":
                self.assertIs(rec["self"], True, row + "\n  posted by the shell's own window")
            elif label.startswith("the shell's own dispatch"):
                self.assertTrue(rec["sourceless"] and rec["origin"] == "", row + "\n  no source, no origin")
            elif label.startswith("a sourceless dispatch"):
                self.assertTrue(rec["sourceless"] and rec["origin"].startswith("http://127.0.0.1:"), row + "\n  no source, the shell's origin")
            elif label.startswith("a same-origin frame nested"):
                self.assertTrue(r["extra"].get("ran"), row + "\n  the nested frame ran its script")
                self.assertTrue(rec["frame"] is None and not rec["self"] and rec["origin"].startswith("http://127.0.0.1:"),
                                row + "\n  a window on the shell's origin that is no iframe of its document")
            elif label.startswith("a same-origin tab"):
                self.assertEqual(r["extra"].get("posted"), "posted", row + "\n  the tab posted through its opener's parent")
                self.assertTrue(rec["frame"] is None and not rec["self"] and rec["origin"].startswith("http://127.0.0.1:"),
                                row + "\n  a window on the shell's origin that is no iframe of its document")
            elif label.startswith("a sandboxed frame"):
                self.assertTrue(r["extra"].get("ran"), row + "\n  the sandboxed frame ran its script")
                self.assertEqual(rec["origin"], "null", row + "\n  the opaque origin")
            else:
                self.fail(row + "\n  a sender this test does not read")
            self.assertIs(r["opened"], False, row + "\n  no pane of the shell: the shortcuts dialog stays closed")
            self.assertIsNone(r["tabKey"], row + "\n  and no session joins the tab keys store")

    def test_chromium(self):
        self._check("chromium")

    def test_firefox(self):
        self._check("firefox")

    def test_webkit(self):
        self._check("webkit")


if __name__ == "__main__":
    unittest.main()
