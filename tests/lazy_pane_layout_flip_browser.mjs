// The browser driver for tests/test_lazy_pane_layout_flip_served.py: a lazy pane's failed load judged across an ACTUAL layout flip, in
// Chromium against a hermetic lab kernel (review round 3 of the lazy panes, 2026-09-19, family one). Opens the served shell at the
// phone viewport (an iPhone descriptor at 390 x 844, under _MOBILE_MQ's 820 px), waits for the two eager panes' sockets, then runs one
// case (cfg.case):
//   A  fail on the phone, then flip: the Waiting pane's first fetch is aborted (Chromium commits an error page and fires load, the shell
//      paints the failed state), the route is lifted, and page.setViewportSize widens the window past the breakpoint, so the engine fires
//      the MediaQueryList change event and the shell's own lazyFlip and retell listeners run: the pane is handed back to data-src and
//      promoted, its document loads and paints, no failed class stands; the flip back to the phone and a tap show a loaded pane.
//   B  flip WHILE loading: the first request for /waiting is held 1.5 s and then aborted (later ones pass); the Waiting tab is tapped on
//      the phone and 300 ms later the window widens, so the phone-armed load listener judges the failure on the DESKTOP: the url goes
//      back under data-src and the pane is promoted once more, the real document loads, exactly one pane-load-failed row is filed and
//      nothing promotes a third time (the token).
//   C  as B, and the desktop's re-promotion FAILS too (the first two requests are aborted, the third would pass): the desktop promotion
//      arms no listener, so the browser's own error page stands with the url under data-src and nothing promotes a third time; without
//      the token minted per promotion the phone-armed listener would judge that second failure too and the promote-fail loop would run
//      until the route passed (extra7-2's refuter executed it).
// Prints one RESULT: JSON line (cfg.resultPath gets the same object). cfg.healthz names the LAB port and is asserted before any request;
// a live kernel is never touched. Chromium alone: WebKit's failure detector is the 30 s backstop (no load event), which would cost 30 s a
// case for the same shell lines. Synthetic sessions only.
import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";

const require = createRequire(process.env.EXT_PKG);
const playwright = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
const now = () => Date.now();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = { case: cfg.case, t: {}, errors: [], requests: [] };
const result = async (extra) => {
  Object.assign(out, extra || {});
  if (cfg.resultPath) { try { fs.writeFileSync(cfg.resultPath, JSON.stringify(out)); } catch (e) { out.resultWriteError = String(e).slice(0, 200); } }
  fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
  try { await browser.close(); } catch (e) { /* closing */ }
  process.exit(0);
};
const die = (why) => result({ died: why });

const healthz = await new Promise((resolve) => {
  const req = http.get(cfg.healthz, (res) => { res.resume(); resolve({ status: res.statusCode }); });
  req.on("error", (e) => resolve({ status: 0, error: String(e) }));
  req.setTimeout(5000, () => { req.destroy(); resolve({ status: 0, error: "timeout" }); });
});
if (healthz.status !== 200) { console.error("lab kernel not healthy: " + JSON.stringify(healthz)); process.exit(4); }

let browser;
try { browser = await playwright.chromium.launch(cfg.launch || {}); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const dev = { ...(playwright.devices["iPhone 14"] || {}) };
delete dev.defaultBrowserType;
const context = await browser.newContext({ ...dev, viewport: { width: 390, height: 844 } });
const page = await context.newPage();
page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });
// every document request for the Waiting pane's page, stamped: the count is the promotions that reached the wire
page.on("request", (r) => { try { const u = new URL(r.url()); if (r.resourceType() === "document" && u.pathname === "/waiting") out.requests.push({ t: now() - (out.t.tap || now()), frame: (r.frame() && r.frame().name()) || "" }); } catch (e) { /* not a url */ } });

// the per-document install: the shell's wsState words (the eager panes' boot wait), and a MutationObserver over every pane iframe's src
// attribute counting the SETS (a record whose old value was absent: a removal is not a set), so the promotions are read off the DOM too
await page.addInitScript(() => {
  const w = window;
  if (w !== w.top || w.__labTopInit) return;
  w.__labTopInit = true;
  w.__labWsNow = {};
  w.addEventListener("message", (e) => { const m = e && e.data; if (m && m.romp === "wsState") w.__labWsNow[m.app] = m.state; });
  w.__labSrcSets = {};
  const arm = () => {
    for (const f of Array.from(document.querySelectorAll("iframe[id^=f-]"))) {
      if (f.__labObserved) continue;
      f.__labObserved = true;
      new MutationObserver((recs) => { for (const r of recs) if (r.attributeName === "src" && r.oldValue === null && f.getAttribute("src") !== null) w.__labSrcSets[f.id.slice(2)] = (w.__labSrcSets[f.id.slice(2)] || 0) + 1; })
        .observe(f, { attributes: true, attributeFilter: ["src"], attributeOldValue: true });
    }
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", arm); else arm();
});

const readPane = () => page.evaluate(() => {
  const f = document.getElementById("f-waiting"), d = f && f.parentElement;
  let url = null, spinGone = null, head = null;
  try { url = f.contentDocument ? f.contentDocument.URL : null; const sp = f.contentDocument && f.contentDocument.getElementById("pane-spin"); spinGone = sp ? sp.classList.contains("gone") : null; head = f.contentDocument ? !!f.contentDocument.getElementById("waiting-head") : null; } catch (e) { url = "ERR:" + String(e).slice(0, 60); }
  return { src: f.getAttribute("src"), lazy: f.getAttribute("data-lazy-src"), dataSrc: f.getAttribute("data-src"), divFailed: !!(d && d.classList.contains("failed")), divLoading: !!(d && d.classList.contains("loading")),
           bodyFailed: document.body.classList.contains("pane-failed"), bodyLoading: document.body.classList.contains("pane-loading"), mobile: !!(window.__rompMobileOn && window.__rompMobileOn()),
           display: getComputedStyle(f).display, url, spinGone, head, sets: (window.__labSrcSets || {}).waiting || 0, msg: (document.getElementById("pane-load-msg") || {}).textContent || "" };
});
const until = async (pred, ms) => { const dl = now() + ms; let r = null; while (now() < dl) { r = await readPane(); if (pred(r)) return { ok: true, r, ms: ms - (dl - now()) }; await sleep(100); } return { ok: false, r, ms }; };
const readDiag = () => { let txt = ""; try { txt = fs.readFileSync(cfg.diag, "utf8"); } catch (e) { return []; } const rows = []; for (const ln of txt.split("\n")) { if (!ln) continue; try { rows.push(JSON.parse(ln)); } catch (e) { /* partial */ } } return rows; };

try {
  await page.goto(cfg.url, { waitUntil: "load", timeout: 40000 });
  const bootDeadline = now() + 30000;
  let up = {};
  while (now() < bootDeadline) { up = await page.evaluate(() => window.__labWsNow || {}); if (up.chat === "up" && up.feed === "up") break; await sleep(150); }
  out.bootUp = Object.keys(up).filter((a) => up[a] === "up").sort();
  out.wid = await page.evaluate(() => { try { return sessionStorage.getItem("romp:wid") || ""; } catch (e) { return ""; } });
  await sleep(cfg.settleMs || 1200);
  out.boot = await readPane();
  const isWaiting = (u) => u.pathname === "/waiting";
  if (cfg.case === "A") {
    const aborter = (route) => route.abort();
    await page.route(isWaiting, aborter);
    out.t.tap = now();
    await page.click("#mtabs button[data-pane=waiting]");
    const failed = await until((r) => r.bodyFailed, 20000);
    out.phoneFailed = { ...failed.r, ms: failed.ok ? failed.ms : -1 };
    await page.unroute(isWaiting, aborter);
    out.t.flip = now();
    await page.setViewportSize({ width: 1200, height: 800 });   // across _MOBILE_MQ's 820 px: the engine fires the MediaQueryList change
    const desk = await until((r) => r.src === "/waiting" && r.url && r.url.endsWith("/waiting") && r.spinGone === true && r.head === true, 25000);
    out.desktop = { ...desk.r, ms: desk.ok ? desk.ms : -1 };
    out.t.flipBack = now();
    await page.setViewportSize({ width: 390, height: 844 });
    await sleep(300);
    await page.click("#mtabs button[data-pane=waiting]");
    await sleep(500);
    out.phoneAgain = await readPane();
  } else {
    let held = 0;
    const abortN = cfg.case === "C" ? 2 : 1;   // C: the desktop's re-promotion fails too
    const gate = async (route) => { if (held === 0) { held = 1; await sleep(cfg.holdMs || 1500); out.t.abort = now(); try { await route.abort(); } catch (e) { /* gone */ } } else if (held < abortN) { held++; try { await route.abort(); } catch (e) { /* gone */ } } else { held++; await route.continue(); } };
    await page.route(isWaiting, gate);
    out.t.tap = now();
    await page.click("#mtabs button[data-pane=waiting]");
    await sleep(300);
    out.midLoad = await readPane();   // loading on the phone, the abort still 1.2 s away
    out.t.flip = now();
    await page.setViewportSize({ width: 1200, height: 800 });
    await sleep(200);
    out.flippedLoading = await readPane();   // the desktop, the phone's promotion still standing (lazyFlip refuses a pane with a src)
    const desk = cfg.case === "C"
      ? await until((r) => r.sets >= 2 && r.src === "/waiting" && r.dataSrc === "/waiting" && out.requests.length >= 2, 25000)   // C: the second promotion reached the wire (and fails there)
      : await until((r) => r.sets >= 2 && r.src === "/waiting" && r.url && r.url.endsWith("/waiting") && r.spinGone === true && r.head === true, 25000);
    out.desktop = { ...desk.r, ms: desk.ok ? desk.ms : -1 };
    await sleep(cfg.case === "C" ? 3000 : 1500);   // room for a third promotion, were one to come (the loop the token closes; C leaves time for two more round trips)
    out.after = await readPane();
    await page.unroute(isWaiting, gate);
    out.routeHeld = held;
  }
  const rows = readDiag().filter((x) => x.wid === out.wid && x.surface === "shell" && (x.what === "pane-load-failed" || x.what === "pane-load-unmarked"));
  out.rows = rows.map((x) => ({ what: x.what, ...(x.data || {}) }));
  await result({});
} catch (e) {
  await die(String(e).slice(0, 600));
}
