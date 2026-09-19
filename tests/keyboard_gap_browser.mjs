// The browser driver for tests/test_keyboard_gap_served.py: the phone shell under an emulated iOS keyboard PAN, against a
// hermetic lab kernel (D1, 2026-09-19). Opens the served dashboard in a playwright browser with the iPhone 14 descriptor,
// waits for the chat pane's composer to lay out, then drives the shell's viewport model by hand and reads the geometry back.
//
// The emulation: an init script on the TOP document (never a pane) replaces window.visualViewport with an EventTarget whose
// height, scale and offsetTop the driver sets, before the shell script parses; the shell's fit() reads window.visualViewport
// fresh on every run and binds its resize and scroll events on the object it finds at parse, so the fake is what it reads
// and what it hears. The layout viewport is the browser's own (innerHeight 844 under the shell's viewport meta). Three
// moves: the keyboard up with iOS's pan (height 508, offsetTop 83, then resize and scroll), the keyboard down (844, 0),
// and a keyboard with no pan (508, 0). After each the driver waits two animation frames (fit() coalesces to one per frame)
// and reads, in the shell's coordinate space: the composer's bottom (the chat iframe's top plus the composer's bottom inside
// its same-origin document), the body's box, #mtabs's box, and the three shell variables.
// Prints one `RESULT:` JSON line; exits 3 when the browser does not launch (the Python side turns that into a skip).
// Never touches a live kernel: cfg.healthz names the LAB port and is asserted before any request. Synthetic sessions only.
import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";

const require = createRequire(process.env.EXT_PKG);
const playwright = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
const engine = cfg.engine || "chromium";
const now = () => Date.now();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = { engine, errors: [], t: {} };

const healthz = await new Promise((resolve) => {
  const req = http.get(cfg.healthz, (res) => { res.resume(); resolve({ status: res.statusCode }); });
  req.on("error", (e) => resolve({ status: 0, error: String(e) }));
  req.setTimeout(5000, () => { req.destroy(); resolve({ status: 0, error: "timeout" }); });
});
if (healthz.status !== 200) { console.error("lab kernel not healthy: " + JSON.stringify(healthz)); process.exit(4); }

let browser;
try { browser = await playwright[engine].launch(cfg.launch || {}); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }

const result = async (extra) => {
  Object.assign(out, extra || {});
  fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
  try { await browser.close(); } catch (e) { /* closing */ }
  process.exit(0);
};

// the phone: the iPhone 14 descriptor at the viewport the design names (under _MOBILE_MQ's 820 px; a coarse pointer, which
// fit()'s visual-viewport branch is gated on), the pattern of tests/return_from_background_browser.mjs
const dev = { ...(playwright.devices["iPhone 14"] || {}) };
delete dev.defaultBrowserType;
const context = await browser.newContext({ ...dev, viewport: { width: 390, height: 844 } });
const page = await context.newPage();
page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });

// the fake visual viewport, on the top document only, before any page script
await page.addInitScript(() => {
  if (window !== window.top) return;
  try {
    const fake = new EventTarget();
    fake.height = 844; fake.width = 390; fake.scale = 1; fake.offsetTop = 0; fake.offsetLeft = 0; fake.pageTop = 0; fake.pageLeft = 0;
    window.__labVV = fake;
    Object.defineProperty(window, "visualViewport", { get: () => fake, configurable: true });
  } catch (e) { window.__labVVError = String(e); }
});

// the geometry, read in the shell's coordinate space
const geo = () => page.evaluate(() => {
  const st = document.documentElement.style;
  const bar = document.getElementById("mtabs");
  const br = bar ? bar.getBoundingClientRect() : null;
  const f = document.getElementById("f-chat");
  const fr = f ? f.getBoundingClientRect() : null;
  const c = f && f.contentDocument ? f.contentDocument.getElementById("composer") : null;
  const cr = c ? c.getBoundingClientRect() : null;
  const body = document.body.getBoundingClientRect();
  const round = (x) => Math.round(x * 100) / 100;
  return {
    innerHeight: window.innerHeight, scrollY: window.scrollY,
    vv: { height: window.visualViewport.height, offsetTop: window.visualViewport.offsetTop, fake: window.visualViewport === window.__labVV },
    appH: st.getPropertyValue("--app-h"), appTop: st.getPropertyValue("--app-top"), mtabsH: st.getPropertyValue("--mtabs-h"),
    bar: br ? { top: round(br.top), bottom: round(br.bottom), height: round(br.height), display: getComputedStyle(bar).display } : null,
    frame: fr ? { top: round(fr.top), bottom: round(fr.bottom) } : null,
    composerBottom: cr && fr ? round(fr.top + cr.bottom) : null,
    composerHeight: cr ? round(cr.height) : null,
    body: { top: round(body.top), bottom: round(body.bottom), position: getComputedStyle(document.body).position },
    labVVError: window.__labVVError || null,
  };
});
// the keyboard's moves: set the fake's geometry, then the events a real keyboard slide fires; two frames for fit()'s rAF
const move = async (height, offsetTop) => {
  await page.evaluate(([h, ot]) => {
    const v = window.__labVV; v.height = h; v.offsetTop = ot;
    v.dispatchEvent(new Event("resize")); v.dispatchEvent(new Event("scroll"));
  }, [height, offsetTop]);
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
  await sleep(50);
  return geo();
};

try {
  out.t.load = now();
  await page.goto(cfg.url, { waitUntil: "load", timeout: 40000 });
  // the composer laid out in the chat pane, the boot splash gone (the panes' first ready, or its 5 s backstop), the bar measured
  const deadline = now() + (cfg.bootTimeoutMs || 30000);
  let ready = false;
  while (now() < deadline) {
    ready = await page.evaluate(() => {
      const f = document.getElementById("f-chat");
      const c = f && f.contentDocument ? f.contentDocument.getElementById("composer") : null;
      const boot = document.getElementById("romp-boot");
      return !!(c && c.getBoundingClientRect().height > 0 && (!boot || boot.classList.contains("gone"))
                && document.documentElement.style.getPropertyValue("--mtabs-h"));
    });
    if (ready) break;
    await sleep(150);
  }
  out.ready = ready;
  out.bootMs = now() - out.t.load;
  await sleep(cfg.settleMs || 500);
  out.rest = await geo();
  out.kbUp = await move(508, 83);        // the keyboard up, with iOS's pan of the visual viewport
  out.kbDown = await move(844, 0);       // the keyboard down: the pan is gone with it
  out.kbNoPan = await move(508, 0);      // a keyboard that does not pan (Android under resizes-visual)
  out.settled = await move(844, 0);
  if (cfg.shots) await page.screenshot({ path: cfg.shots + "-settled.png" }).catch(() => {});
  await result({});
} catch (e) {
  await result({ died: String(e).slice(0, 600) });
}
