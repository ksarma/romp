#!/usr/bin/env python3
"""The bottom bar's API health cell, driven in a real browser (review round 1, 2026-09-07).

The shell page is kernel-served HTML with inline CSS and JS, so it has no jsdom harness: the source pins in
tests/test_api_health_rail.py and tests/test_kernel_pane_rail.py hold the SHAPE, and this module holds the
BEHAVIOR those pins approximate. A scratch copy of km._landing() is served from a temp directory over plain
HTTP with no kernel behind it (every fetch 404s and the shell socket never opens, which is exactly the
pre-frame world the cell's hidden rule exists for), and playwright's chromium drives it: frames are handed
to window.__rompApiHealth directly, presses are dispatched as pointer events, and the driver reports what
the DOM did. Skips LOUDLY without the extension's node deps or a browser (CI installs none), the way
tests/test_awaiting_box_sync.py does.

Synthetic only: an invented sid family, the notes-api demo's session names, no real data."""
import functools
import http.server
import json
import os
import subprocess
import tempfile
import threading
import unittest
from romp_load import load_source

# Hermetic state BEFORE the loads: they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
EXT = os.path.join(os.path.dirname(HERE), "vscode-extension")
km = load_source("romp_kernel_apih_browser", os.path.join(BIN, "romp-kernel"))

SID = "77777777-aaaa-4bbb-8ccc-00000000000"     # + a digit: the rail test module's private synthetic family

DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
page.on("pageerror", () => {});                       // the scratch page has no kernel: its sockets and fetches fail
await page.goto(cfg.url);
await page.waitForFunction(() => typeof window.__rompApiHealth === "function", null, { timeout: 20000 });
const R = await page.evaluate((SID) => {
  const R = { err: {} };
  const step = (name, fn) => { try { fn(); } catch (e) { R.err[name] = String(e && e.stack || e); } };
  const el = document.getElementById("rail-api"), txt = el.querySelector(".ah-text");
  const tip = () => document.getElementById("ah-tip");
  const back = document.getElementById("ru-back");
  const disp = (n) => getComputedStyle(n).display;
  const row = (i) => ({ sid: SID + i, name: ["web", "api", "tests", "docs"][i], color: null, kind: "blocked",
                        cls: "529", status: 529, since: 1700000000 + i, suppressed: false });
  const frame = (over) => Object.assign({ type: "apiHealth", state: "degraded", cls: "529", reason: "",
    text: "overloaded · 1 waiting", waiting: 1, retrying: 0, blocked: 1, since: 1700000000, tmux: 0,
    sessions: [row(1)] }, over || {});
  const btn = () => tip().querySelector("button[data-act=pause]");
  // 1. before any frame: the cell is not displayed (the hidden attribute must beat .ru-w's display rule)
  R.preFrameHidden = el.hidden;
  R.preFrameDisplay = disp(el);
  R.usageEmptyDisplay = disp(document.getElementById("rail-usage"));
  R.role = el.getAttribute("role"); R.tabindex = el.getAttribute("tabindex");
  // 2. the first frame reveals it and names the state for a screen reader
  window.__rompApiHealth(frame());
  R.firstFrameDisplay = disp(el); R.firstFrameText = txt.textContent; R.ariaLabel = el.getAttribute("aria-label");
  step('hover', () => {
  // 3. the hover surface is inert: no button, no data-act; a growing frame re-anchors it above the rail
  el.dispatchEvent(new MouseEvent("mouseenter", { bubbles: false, clientX: el.getBoundingClientRect().left + 10 }));
  R.hoverShown = tip().style.display === "block";
  R.hoverButtons = tip().querySelectorAll("button").length;
  R.hoverActs = tip().querySelectorAll("[data-act]").length;
  const railTop = el.getBoundingClientRect().top;
  const b1 = tip().getBoundingClientRect();
  window.__rompApiHealth(frame({ text: "overloaded · 3 waiting", waiting: 3, blocked: 3, sessions: [row(1), row(2), row(3)] }));
  const b2 = tip().getBoundingClientRect();
  R.reanchor = { railTop, before: { top: b1.top, bottom: b1.bottom, h: b1.height }, after: { top: b2.top, bottom: b2.bottom, h: b2.height } };
  el.dispatchEvent(new MouseEvent("mouseleave"));
  R.hoverHidden = tip().style.display === "none";
  });
  step('keyboard', () => {
  // 4. keyboard: Enter opens the pinned detail and moves focus into it; Escape closes and puts focus back
  el.focus();
  el.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  R.kbOpened = tip().style.display === "block" && tip().classList.contains("ru-modal") && back.classList.contains("on");
  R.kbFocusInTip = tip().contains(document.activeElement);
  R.tipRole = tip().getAttribute("role");
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  R.kbClosed = tip().style.display === "none" && !back.classList.contains("on");
  R.kbFocusBack = document.activeElement === el;
  });
  step('usage', () => {
  // 5. an open usage modal is closed first, explicitly, so the shared backdrop never serves two modals
  let usageClosed = false;
  window.__rompUsageClose = () => { usageClosed = true; back.classList.remove("on"); window.__rompUsageClose = null; };
  back.classList.add("on");
  el.click();
  R.usageClosedFirst = usageClosed && tip().style.display === "block" && tip().classList.contains("ru-modal");
  });
  step('clicksafe', () => {
  // 6. click-safe across a frame: a press held on the button defers the re-render; the release flushes it
  const sent = []; window.__rompShellSend = (o) => { sent.push(o); return true; };
  const b0 = btn(); R.pinnedHasButton = !!b0;
  b0.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
  window.__rompApiHealth(frame({ text: "overloaded · 2 waiting", waiting: 2, blocked: 2, sessions: [row(1), row(2)] }));
  R.heldKeepsNode = document.contains(b0);
  R.heldKeepsText = /1 waiting/.test(tip().textContent);
  b0.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
  b0.click();                                          // the click lands on the button that was pressed
  R.clickSent = sent.map((o) => o.type + ":" + String(o.value));
  R.flushedOnClick = /2 waiting/.test(tip().textContent);
  });
  step('ack', () => {
  // 7. the acknowledgment survives frames until one confirms the flip
  const b1n = btn();
  R.ack = { disabled: b1n.disabled, label: b1n.textContent, acted: b1n.classList.contains("romp-acted") };
  window.__rompApiHealth(frame({ text: "overloaded · 2 waiting", waiting: 2, blocked: 2, since: 1700000005, sessions: [row(1), row(2)] }));
  const b2n = btn();
  R.ackHeld = { disabled: b2n.disabled, label: b2n.textContent, acted: b2n.classList.contains("romp-acted") };
  window.__rompApiHealth(frame({ state: "paused", reason: "manual", text: "paused by you · 2 waiting", waiting: 2, blocked: 2, sessions: [row(1), row(2)] }));
  const b3n = btn();
  R.confirmed = { disabled: b3n.disabled, label: b3n.textContent, acted: b3n.classList.contains("romp-acted") };
  });
  step('failed', () => {
  // 8. a failed send restores the label, drops the acted styling and says why
  window.__rompShellSend = () => false;
  const bf = btn();
  bf.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
  bf.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
  bf.click();
  const b4n = btn();
  R.failed = { disabled: b4n.disabled, label: b4n.textContent, acted: b4n.classList.contains("romp-acted"),
               hint: (tip().querySelector(".ah-hint") || {}).textContent || "" };
  });
  step('row', () => {
  // 9. a session row opens that session the way the feed's own links do: openSession on the socket,
  //    no pane toggle, nothing persisted
  const sent2 = []; window.__rompShellSend = (o) => { sent2.push(o); return true; };
  let toggled = 0; window.__rompPaneToggle = () => { toggled++; };
  const r0 = tip().querySelector(".ah-row[data-act=reveal]");
  R.rowHasAct = !!r0;
  if (r0) { r0.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true })); r0.dispatchEvent(new PointerEvent("pointerup", { bubbles: true })); r0.click(); }
  R.rowSent = sent2; R.rowToggled = toggled; R.rowClosed = tip().style.display === "none";
  });
  step('light', () => {
  // 10. the light theme's ok dot
  document.body.classList.add("theme-light");
  window.__rompApiHealth(frame({ state: "ok", cls: "", text: "ok", waiting: 0, blocked: 0, since: 0, sessions: [] }));
  R.lightDot = getComputedStyle(el.querySelector(".ah-dot")).backgroundColor;
  R.lightDotOpacity = getComputedStyle(el.querySelector(".ah-dot")).opacity;
  });
  return R;
}, cfg.sid);
if (cfg.shots) await page.screenshot({ path: cfg.shots });
fs.writeSync(1, "RESULT:" + JSON.stringify(R) + "\n");
await browser.close();
process.exit(0);
"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class ServedCell(unittest.TestCase):
    """One browser run over the scratch page; each test reads one facet of what it reported."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served cell needs a browser")
        cls.lab = tempfile.mkdtemp(prefix="apih-browser-")
        html = km._landing()
        with open(os.path.join(cls.lab, "index.html"), "w") as f:
            f.write(html if isinstance(html, str) else html.decode("utf-8"))
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=cls.lab))
        cls.thr = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thr.start()
        cfg = os.path.join(cls.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump({"url": "http://127.0.0.1:%d/" % cls.srv.server_address[1], "sid": SID,
                       "shots": os.environ.get("APIH_BROWSER_SHOT", "")}, f)
        driver = os.path.join(cls.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=180,
                           env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        cls.srv.shutdown()
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box: the served cell needs one (CI installs none)")
        if p.returncode != 0:
            raise AssertionError("driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        if line is None:
            raise AssertionError("driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        cls.R = json.loads(line[len("RESULT:"):])

    def test_the_cell_is_not_displayed_before_the_first_frame(self):
        # the HIGH finding: the UA's [hidden]{display:none} loses to the author rule .ru-w{display:flex},
        # so without an author [hidden] rule the rail showed a gray 'API ok' from page load
        self.assertTrue(self.R["preFrameHidden"], "the markup ships the attribute")
        self.assertEqual(self.R["preFrameDisplay"], "none", "and the attribute must actually hide it: %r" % self.R)
        self.assertEqual(self.R["firstFrameDisplay"], "flex", "the first frame reveals the cell")
        self.assertEqual(self.R["firstFrameText"], "overloaded · 1 waiting")


if __name__ == "__main__":
    unittest.main()
