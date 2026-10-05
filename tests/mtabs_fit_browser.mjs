// The browser driver for tests/test_mtabs_fit_served.py: the phone layout's bottom bar (#mtabs) measured in one engine,
// against a hermetic lab kernel. Opens the served dashboard with the iPhone 14 descriptor (Firefox without isMobile, which
// Playwright does not support there), once per tab set: the default set, and the set with the Files tab on (the gear's
// Files-control setting, written to the store before the page parses, the read the shell makes at boot). In each it takes
// the window through cfg.viewports (portrait and landscape phones), waits for the webfont and two frames, and reads, in
// the shell's coordinate space: the bar's box, its scroll and client widths, every control the bar shows (each button
// not display:none: the pane tabs, the action buttons, the bell), each control's box, whether its label fits inside it,
// and the element at its centre (elementFromPoint, which answers null past the window's edge), the bar's natural
// one-row width (the bar laid out once at max-content without wrapping, read synchronously and restored before the
// next paint), the reserved height --mtabs-h, the shown pane's iframe box, and the document's scroll width.
// Then the change the boot read cannot see: on the default set at cfg.dynamicViewport, the Files tab turned on the way
// the gear turns it on (a write of the settings key from a same-origin pane document, so this window hears the storage
// event the shell's pane controller acts on), with no resize, and the same reading after two frames.
// And the desktop: a plain context (no descriptor, a fine pointer) at cfg.desktopViewport, where the bar must stay hidden.
// Writes the readings as JSON to cfg.result and prints one `RESULT-FILE:` line naming it; exits 3 when the browser does not
// launch (the Python side turns that into a skip).
// Never touches a live kernel: cfg.healthz names the LAB port and is asserted before any request. No sessions.
import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";

const require = createRequire(process.env.EXT_PKG);
const playwright = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
const engine = cfg.engine || "chromium";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = { engine, errors: [], sets: {}, dynamic: null, desktop: null };

const healthz = await new Promise((resolve) => {
  const req = http.get(cfg.healthz, (res) => { res.resume(); resolve({ status: res.statusCode }); });
  req.on("error", (e) => resolve({ status: 0, error: String(e) }));
  req.setTimeout(5000, () => { req.destroy(); resolve({ status: 0, error: "timeout" }); });
});
if (healthz.status !== 200) { console.error("lab kernel not healthy: " + JSON.stringify(healthz)); process.exit(4); }

let browser;
try { browser = await playwright[engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }

const phone = { ...(playwright.devices["iPhone 14"] || {}) };
delete phone.defaultBrowserType;
if (engine === "firefox") delete phone.isMobile;   // playwright: isMobile is not supported in Firefox

// the reading, in the page; a string so the same function runs in every engine unchanged
const READ = () => {
  const r = (x) => Math.round(x * 100) / 100;
  const bar = document.getElementById("mtabs");
  const vw = window.innerWidth, vh = window.innerHeight;
  const bs = getComputedStyle(bar);
  const br = bar.getBoundingClientRect();
  const shownButtons = Array.from(bar.querySelectorAll("button")).filter((b) => getComputedStyle(b).display !== "none");
  // the natural one-row width, and each control's natural width (its width when nothing squeezes it): the bar at max-content
  // with no wrapping, read and restored synchronously (no paint between)
  const saved = bar.getAttribute("style");
  bar.style.setProperty("flex-wrap", "nowrap", "important");
  bar.style.setProperty("width", "max-content", "important");
  bar.style.setProperty("right", "auto", "important");
  const natural = r(bar.getBoundingClientRect().width);
  const naturalW = new Map(shownButtons.map((b) => [b, r(b.getBoundingClientRect().width)]));
  if (saved === null) bar.removeAttribute("style"); else bar.setAttribute("style", saved);
  const controls = shownButtons.map((b) => {
    const c = b.getBoundingClientRect();
    let hit = false;
    if (c.width > 0 && c.height > 0) {
      const at = document.elementFromPoint(c.left + c.width / 2, c.top + c.height / 2);
      hit = !!at && (at === b || b.contains(at));
    }
    return { key: b.getAttribute("data-pane") || b.id || b.getAttribute("data-act") || "?", tab: b.hasAttribute("data-pane"),
             left: r(c.left), right: r(c.right), top: r(c.top), bottom: r(c.bottom), w: r(c.width), h: r(c.height),
             naturalW: naturalW.get(b), labelFits: b.scrollWidth <= b.clientWidth + 0.5, hit };
  });
  const div = bar.querySelector(".mtabs-div");
  const dr = div ? div.getBoundingClientRect() : null;
  const shown = document.querySelector("iframe.m-on");
  const sr = shown ? shown.getBoundingClientRect() : null;
  return {
    vw, vh, mobile: window.__rompMobileOn ? window.__rompMobileOn() : null, display: bs.display,
    bar: { left: r(br.left), right: r(br.right), top: r(br.top), bottom: r(br.bottom), w: r(br.width), h: r(br.height),
           offsetH: bar.offsetHeight, scrollW: bar.scrollWidth, clientW: bar.clientWidth, borderTop: parseFloat(bs.borderTopWidth) || 0,
           padBottom: parseFloat(bs.paddingBottom) || 0 },
    natural, mtabsH: document.documentElement.style.getPropertyValue("--mtabs-h"),
    divider: dr ? { left: r(dr.left), right: r(dr.right), top: r(dr.top), bottom: r(dr.bottom), w: r(dr.width), h: r(dr.height) } : null,
    pane: sr ? { id: shown.id, top: r(sr.top), bottom: r(sr.bottom) } : null,
    docScrollW: document.documentElement.scrollWidth,
    bell: (() => { const b = document.getElementById("mbell"); return b ? { hidden: b.hidden, display: getComputedStyle(b).display } : null; })(),
    fonts: document.fonts ? document.fonts.check("600 12px Inter") : null,
    controls,
  };
};
const read = (page) => page.evaluate("(" + READ.toString() + ")()");
const frames = (page) => page.evaluate(() => new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(() => res()))));

// a phone page on one tab set, booted: the bar laid out, the boot splash gone (the panes' first ready, or its backstop), the webfont in
async function boot(files) {
  const context = await browser.newContext({ ...phone, viewport: { width: 390, height: 844 } });
  if (files) await context.addInitScript(() => { try { localStorage.setItem("romp:settings", JSON.stringify({ showFilesControl: true })); } catch (e) { /* no store */ } });
  const page = await context.newPage();
  page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });
  await page.goto(cfg.url, { waitUntil: "load", timeout: 40000 });
  await page.waitForSelector("#mtabs", { timeout: 20000 });
  await page.waitForFunction(() => { const b = document.getElementById("romp-boot"); return !b || b.classList.contains("gone"); }, null, { timeout: 30000 });
  await page.evaluate(() => (document.fonts ? document.fonts.ready.then(() => true) : true));
  return { context, page };
}

try {
  for (const [name, files] of [["default", false], ["files", true]]) {
    const { context, page } = await boot(files);
    const rows = [];
    for (const [w, h] of cfg.viewports) {
      await page.setViewportSize({ width: w, height: h });
      await frames(page);
      await sleep(cfg.settleMs || 100);
      await frames(page);
      rows.push({ vp: [w, h], ...(await read(page)) });
    }
    out.sets[name] = rows;
    await context.close();
  }
  // the Files tab turned on with no resize: the bar's height changes, and the reservation must follow it
  {
    const { context, page } = await boot(false);
    const [w, h] = cfg.dynamicViewport;
    await page.setViewportSize({ width: w, height: h });
    await frames(page);
    await sleep(cfg.settleMs || 100);
    await frames(page);
    const before = await read(page);
    const pane = page.frames().find((f) => f !== page.mainFrame() && /\/chat/.test(f.url()));
    if (!pane) throw new Error("no chat pane frame to write the setting from");
    await pane.evaluate(() => { localStorage.setItem("romp:settings", JSON.stringify({ showFilesControl: true })); });
    await page.waitForFunction(() => { const b = document.querySelector("#mtabs button[data-pane=files]"); return !!b && getComputedStyle(b).display !== "none"; }, null, { timeout: 10000 });
    await frames(page);
    await sleep(cfg.settleMs || 100);
    await frames(page);
    out.dynamic = { vp: [w, h], before, after: await read(page) };
    await context.close();
  }
  // the desktop: a fine pointer at a desktop size, where the phone bar is not shown at all
  {
    const context = await browser.newContext({ viewport: { width: cfg.desktopViewport[0], height: cfg.desktopViewport[1] } });
    const page = await context.newPage();
    page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });
    await page.goto(cfg.url, { waitUntil: "load", timeout: 40000 });
    await page.waitForSelector("#mtabs", { state: "attached", timeout: 20000 });
    out.desktop = await page.evaluate(() => {
      const bar = document.getElementById("mtabs"), rail = document.querySelector(".pane-rail");
      return { display: getComputedStyle(bar).display, mobile: window.__rompMobileOn ? window.__rompMobileOn() : null,
               railDisplay: rail ? getComputedStyle(rail).display : null };
    });
    await context.close();
  }
} catch (e) {
  out.died = String(e).slice(0, 600);
}
// the result goes to the file the Python side names (cfg.result): one write to a pipe can stop at the pipe's buffer, and these
// readings run past 64 KB
fs.writeFileSync(cfg.result, JSON.stringify(out));
fs.writeSync(1, "RESULT-FILE:" + cfg.result + "\n");
try { await browser.close(); } catch (e) { /* closing */ }
process.exit(0);
