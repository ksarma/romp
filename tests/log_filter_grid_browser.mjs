// The browser driver for tests/test_log_filter_grid_served.py: the Log's filter grid (the "show" toggles at the top of the
// Log panel, one per kind) laid out in a real engine against a hermetic lab kernel (item 4d, 2026-10-04).
//
// Two contexts, one page each. The phone: playwright's iPhone 14 descriptor (isMobile dropped in Firefox, which does not
// support it), so the shell is in its phone layout, and the Log opened by a click on the phone bar's triangle (#merr) at
// cfg.openWidth (390 px: the bar itself is wider than the narrowest phones, so the triangle is off the screen at 320 px, a
// separate defect this test does not cover). The page is then resized through cfg.phoneWidths (the panel is pure CSS, so a
// resize re-lays it out in place), and the geometry is read at each width after two animation frames. Each context waits for
// the shell to finish booting first (bootDone below). The desktop: a plain context (a fine pointer) at each of
// cfg.desktopWidths, the Log opened by the shell's opener (window.__rompOpenErrs, the function the gear's Open log button and
// the command palette call; tests/test_log_opener_moved_served.py drives the gear itself). Before opening, the page logs one
// synthetic entry of every kind the filter grid shows (the kinds are read from the grid's own buttons), so the list under
// the grid is populated the way a busy Log is.
//
// At each width it reads: the viewport and the document's scroll width (a page that scrolls sideways), the panel's and the
// filter bar's boxes (the bar's content box: its padding stripped), the grid's box and its computed column tracks, and for
// every toggle its box, the width its label needs (the text's own width plus the chip's padding and border), its font size,
// its display and visibility, and whether a point at its centre hits it (reachable by a tap).
// Prints one `RESULT:` JSON line, written whole however long it is (writeAll below); exits 3 when the browser does not
// launch (the Python side turns that into a skip).
// Never touches a live kernel: cfg.healthz names the LAB port and is asserted before any request. Synthetic entries only.
import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";

const require = createRequire(process.env.EXT_PKG);
const playwright = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
const engine = cfg.engine || "chromium";
const out = { engine, errors: [], phone: [], desktop: [] };

const healthz = await new Promise((resolve) => {
  const req = http.get(cfg.healthz, (res) => { res.resume(); resolve({ status: res.statusCode }); });
  req.on("error", (e) => resolve({ status: 0, error: String(e) }));
  req.setTimeout(5000, () => { req.destroy(); resolve({ status: 0, error: "timeout" }); });
});
if (healthz.status !== 200) { console.error("lab kernel not healthy: " + JSON.stringify(healthz)); process.exit(4); }

let browser;
try { browser = await playwright[engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }

// The whole RESULT line reaches stdout before the exit. Requiring playwright leaves fd 1 non-blocking, and one writeSync to
// a pipe then writes only what the pipe has room for (64 KiB) and drops the rest, so the line is written from a Buffer in a
// loop, advancing by the bytes each call reports and retrying after EAGAIN (the pipe full until the test reads it). It
// stays synchronous: the "died" paths below await result() and rely on it never returning, which process.exit keeps true.
const writeAll = (text) => {
  const buf = Buffer.from(text, "utf8"), nap = new Int32Array(new SharedArrayBuffer(4));
  for (let off = 0; off < buf.length;) {
    try { off += fs.writeSync(1, buf, off, buf.length - off); }
    catch (e) { if (e.code !== "EAGAIN") throw e; Atomics.wait(nap, 0, 0, 5); }
  }
};
const result = async (extra) => {
  Object.assign(out, extra || {});
  writeAll("RESULT:" + JSON.stringify(out) + "\n");
  try { await browser.close(); } catch (e) { /* closing */ }
  process.exit(0);
};
const frames = (page) => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));

// the geometry, in the shell's coordinate space
const measure = (page) => page.evaluate(() => {
  const box = (el) => { if (!el) return null; const r = el.getBoundingClientRect(); return { l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height }; };
  const de = document.documentElement;
  const panel = document.getElementById("rerr-panel"), bar = document.getElementById("rerr-filters"), grid = document.getElementById("rerr-fgrid");
  const bcs = getComputedStyle(bar), br = bar.getBoundingClientRect();
  const btns = Array.from(grid.children).map((b) => {
    const r = b.getBoundingClientRect(), cs = getComputedStyle(b);
    const rg = document.createRange(); rg.selectNodeContents(b);
    const need = rg.getBoundingClientRect().width + parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight)
      + parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderRightWidth);
    const hit = document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2);
    return { kind: (/\bk-(\S+)/.exec(b.className) || [])[1] || "", text: b.textContent, l: r.left, r: r.right, t: r.top, b: r.bottom,
      w: r.width, h: r.height, need, fontSize: cs.fontSize, display: cs.display, visibility: cs.visibility, hit: hit === b };
  });
  const x0 = window.scrollX; window.scrollTo(100000, window.scrollY); const scrollX = window.scrollX; window.scrollTo(x0, window.scrollY);
  return { vw: window.innerWidth, docSW: de.scrollWidth, docCW: de.clientWidth, scrollX,
    mobile: !!(window.__rompMobileOn && window.__rompMobileOn()), logOpen: !document.getElementById("rerr-back").hidden,
    panel: box(panel), bar: box(bar),
    barContent: { l: br.left + parseFloat(bcs.borderLeftWidth) + parseFloat(bcs.paddingLeft), r: br.right - parseFloat(bcs.borderRightWidth) - parseFloat(bcs.paddingRight) },
    grid: box(grid), cols: getComputedStyle(grid).gridTemplateColumns, btns };
});

// booted: the Log's opener published, its toggles built, and the boot splash removed from the DOM (it covers the whole window
// at z-index 9999 until the panes' first ready or its 5 s backstop, then fades and is removed; a point under it hits the splash)
const bootDone = () => !!window.__rompOpenErrs && !!document.querySelector("#rerr-fgrid .rerr-fbtn") && !document.getElementById("romp-boot");

// one synthetic entry of every kind the grid shows, through the Log's one write path
const seed = (page) => page.evaluate(() => {
  const kinds = Array.from(document.querySelectorAll("#rerr-fgrid .rerr-fbtn")).map((b) => (/\bk-(\S+)/.exec(b.className) || [])[1] || "");
  kinds.forEach((k, i) => window.__rompNotify(k, "Synthetic " + k + " entry " + i + " for the notes-api lab"));
  return kinds;
});

// --- the phone ---
{
  const dev = { ...(playwright.devices["iPhone 14"] || {}) };
  delete dev.defaultBrowserType;
  const opts = { ...dev, viewport: { width: cfg.openWidth, height: cfg.phoneHeight } };
  if (engine === "firefox") delete opts.isMobile;   // playwright: isMobile is not supported in Firefox
  const ctx = await browser.newContext(opts);
  const page = await ctx.newPage();
  page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });
  await page.goto(cfg.url);
  try { await page.waitForFunction(bootDone, null, { timeout: cfg.bootTimeoutMs }); }
  catch (e) { await result({ died: "the phone shell never finished booting: " + String(e).slice(0, 200) }); }
  out.kinds = await seed(page);
  await page.click("#merr");
  try { await page.waitForFunction(() => !document.getElementById("rerr-back").hidden, null, { timeout: 8000 }); }
  catch (e) { await result({ died: "the Log never opened on the triangle's click: " + String(e).slice(0, 200) }); }
  for (const w of cfg.phoneWidths) {
    await page.setViewportSize({ width: w, height: cfg.phoneHeight });
    await frames(page);
    out.phone.push({ w, m: await measure(page) });
  }
  await ctx.close();
}

// --- the desktop ---
for (const w of cfg.desktopWidths) {
  const ctx = await browser.newContext({ viewport: { width: w, height: cfg.desktopHeight } });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });
  await page.goto(cfg.url);
  try { await page.waitForFunction(bootDone, null, { timeout: cfg.bootTimeoutMs }); }
  catch (e) { await result({ died: "the desktop shell never finished booting: " + String(e).slice(0, 200) }); }
  await seed(page);
  await page.evaluate(() => window.__rompOpenErrs());
  await frames(page);
  out.desktop.push({ w, m: await measure(page) });
  await ctx.close();
}
await result();
