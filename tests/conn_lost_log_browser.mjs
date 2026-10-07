// The browser driver for tests/test_conn_lost_log_served.py: one return from the background against a hermetic lab
// kernel, and what the shell's Log wrote about it. Opens the served dashboard shell (a phone or a desktop window) in a
// playwright browser, waits for every eager pane socket and the shell's own socket to open, emulates a suspend and a
// return, and records every write to the Log (window.__rompNotify, stamped), the Log's entries and their unread state
// at each read, the Log control's digit and red cue, and the socket words the panes told the shell.
//
// The emulation is tests/return_from_background_browser.mjs's, cut down to what the Log needs:
//   * document.visibilityState and document.hidden read a per-document flag (an init script, and a late pass over any
//     frame it missed); the driver flips the flag and dispatches `visibilitychange` in the top document and then every
//     frame, in one task.
//   * every WebSocket dial is routed (page.routeWebSocket on /ws). Outside an outage a dial passes through to the lab
//     kernel. cfg.fin says when the held sockets close: "suspend" closes them at the suspend (the OS dropped them while
//     the page slept), "return" right after the return's dispatch (the FIN a thawed page receives after its handlers ran).
//   * cfg.regime: "healthy" (no outage: every redial passes at once), "refused" (from the suspend every new dial is closed
//     at once, never connecting: the kernel is down), "refused-panes" (the same for every pane dial while the shell's own
//     dial passes: the pane's own reconnect fails while the page's link stands), "hung" (every new dial stays CONNECTING
//     until the outage ends, the phone's dead path). An outage lasts cfg.outageMs from the return.
//   * cfg.regime "slow" (the review of item 4b, 2026-10-03): from the suspend every dial waits in ONE line, as Chromium and
//     Firefox hold each WebSocket handshake to a host until the one ahead of it has opened or failed (RFC 6455 section 4.1); a
//     routed socket is a mock in the page, so the engine's own line does not apply here and the driver keeps it. A dial's turn
//     comes when the dial ahead has opened or been cut, its handshake then takes cfg.handshakeMs, and it passes unless the page
//     cut it first (the page's own 15 s connect cut, a timer); a dial the page cuts gives up its place at once. Every
//     handshake succeeds: a slow network, not an outage. cfg.fin "return-panes-first" closes the pane sockets before the
//     shell's, so the panes redial while the shell's link still stands and the shell's own redial waits behind theirs.
// Writes its result to cfg.resultPath and prints one short `RESULT:` line naming it; exits 3 when the browser does not
// launch (the Python side turns that into a skip). Never touches a live kernel: cfg.healthz names the LAB port and is
// asserted before any request. Synthetic sessions only.
import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";

const require = createRequire(process.env.EXT_PKG);
const playwright = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
const engine = cfg.engine || "chromium";
const EAGER = cfg.eagerApps || [];
if (!EAGER.length) { console.error("empty eager set in cfg"); process.exit(5); }   // an empty set would end the boot wait with nothing witnessed
const now = () => Date.now();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = { engine, shell: cfg.shell, regime: cfg.regime, fin: cfg.fin, outageMs: cfg.outageMs, t: {}, dials: [], errors: [] };

const healthz = await new Promise((resolve) => {
  const req = http.get(cfg.healthz, (res) => { res.resume(); resolve({ status: res.statusCode }); });
  req.on("error", (e) => resolve({ status: 0, error: String(e) }));
  req.setTimeout(5000, () => { req.destroy(); resolve({ status: 0, error: "timeout" }); });
});
if (healthz.status !== 200) { console.error("lab kernel not healthy: " + JSON.stringify(healthz)); process.exit(4); }

let browser;
try { browser = await playwright[engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
// The full result goes to cfg.resultPath and the RESULT: line names it (review round 1 of item 4b, 2026-10-04; the pattern of
// tests/return_from_background_browser.mjs). Loading playwright leaves stdout non-blocking, so one writeSync to a pipe writes
// what the pipe has room for and the rest is lost: up to 64 KiB, and 8 KiB on a loaded machine (a user past
// fs.pipe-user-pages-soft gets minimum-size pipes, pipe(7)), where a 24 KB record was cut at 8 KiB and the Python side read
// half a line. The line carries the died reason too.
const result = async (extra) => {
  Object.assign(out, extra || {});
  const line = { resultPath: cfg.resultPath || null };
  if (out.died) line.died = String(out.died).slice(0, 600);
  try { fs.writeFileSync(cfg.resultPath, JSON.stringify(out)); } catch (e) { line.resultWriteError = String(e).slice(0, 200); }
  fs.writeSync(1, "RESULT:" + JSON.stringify(line) + "\n");
  try { await browser.close(); } catch (e) { /* closing */ }
  process.exit(0);
};

let ctxOpts;
if (cfg.shell === "phone") {
  const dev = { ...(playwright.devices["iPhone 14"] || {}) };
  delete dev.defaultBrowserType;
  ctxOpts = { ...dev, viewport: { width: 390, height: 844 } };
  if (engine === "firefox") delete ctxOpts.isMobile;   // playwright: isMobile is not supported in Firefox
} else {
  ctxOpts = { viewport: { width: 1600, height: 760 } };
}
const context = await browser.newContext(ctxOpts);
const page = await context.newPage();
page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });

// --- the routed WebSocket path ---
const state = { outage: false, slow: false, phase: "boot" };
let outageEnded = null, endOutage = null;
const live = new Set();
const liveApp = new Map();   // each held socket's app, so cfg.fin "return-panes-first" can close the shell's last
let lineTail = Promise.resolve();   // the slow regime's one line: settled when the dial at its end has opened or been cut
const appOf = (u) => { try { return new URL(u).searchParams.get("app") || "?"; } catch (e) { return "?"; } };
const wire = (ws, d) => {
  const server = ws.connectToServer();
  server.onMessage((m) => ws.send(m));
  ws.onMessage((m) => server.send(m));
  server.onClose((code, reason) => { live.delete(ws); try { ws.close({ code: code || 1000, reason: reason || "" }); } catch (e) { /* closed */ } });
  ws.onClose(() => { live.delete(ws); try { server.close(); } catch (e) { /* closed */ } });
  live.add(ws);
  liveApp.set(ws, d.app);
};
const outageFor = (app) => state.outage && (cfg.regime === "refused" || cfg.regime === "hung" || (cfg.regime === "refused-panes" && app !== "shell"));
await page.routeWebSocket((u) => /\/ws(\?|$)/.test(u.pathname + (u.search || "")), async (ws) => {
  const d = { app: appOf(ws.url()), t: now(), phase: state.phase };
  out.dials.push(d);
  try {
    if (state.slow) {
      let cutNow = null;
      const cutP = new Promise((r) => { cutNow = r; });
      ws.onClose((code) => { d.cutByPage = true; d.cutT = now(); cutNow(); try { ws.close({ code: code || 1000, reason: "lab-cut" }); } catch (e) { /* closed */ } });
      const ahead = lineTail;
      let done = null;
      lineTail = new Promise((r) => { done = r; });
      try {
        await ahead;
        if (!d.cutByPage) { d.turnT = now(); await Promise.race([sleep(cfg.handshakeMs), cutP]); }
        if (d.cutByPage) { d.verdict = "slow-cut"; return; }
        d.verdict = "passed"; d.openT = now(); wire(ws, d);
      } finally { done(); }
      return;
    }
    if (!outageFor(d.app)) { d.verdict = "passed"; wire(ws, d); return; }
    if (cfg.regime !== "hung") { d.verdict = "refused"; await ws.close({ code: 1006, reason: "lab-refused" }); return; }
    d.verdict = "hung";   // the handler stays pending, so the page-side socket stays CONNECTING; a cut by the page completes it
    ws.onClose((code) => { d.cutByPage = true; d.cutT = now(); try { ws.close({ code: code || 1000, reason: "lab-cut" }); } catch (e) { /* closed */ } });
    await outageEnded;
    if (d.cutByPage) { d.verdict = "hung-cut"; return; }
    d.verdict = "hung-released";
    wire(ws, d);
  } catch (e) { d.error = String(e).slice(0, 200); }
});

// --- the per-document install: the visibility override; in the top document the recorders ---
const install = () => {
  const w = window;
  if (document.__labInit) return false;   // per DOCUMENT: an iframe leaving about:blank can keep its Window (Firefox, WebKit)
  document.__labInit = true;
  if (w.__labHidden === undefined) w.__labHidden = false;
  try {
    Object.defineProperty(document, "visibilityState", { get: () => (w.__labHidden ? "hidden" : "visible"), configurable: true });
    Object.defineProperty(document, "hidden", { get: () => !!w.__labHidden, configurable: true });
  } catch (e) { /* recorded by the boot read: a frame without the override reads :MISSING there */ }
  if (w === w.top && !w.__labTopInit) {
    w.__labTopInit = true;
    w.__labWs = [];        // every pane word to the shell about its socket: {romp:'wsState'} and, at the fix, {romp:'wsFail'}
    w.__labNotify = [];    // every write to the Log, stamped: the center's one write path, wrapped the moment it is assigned
    w.__labCue = [];       // the Log control's red cue and digit, at each change
    w.addEventListener("message", (e) => {
      const m = e && e.data;
      if (!m || (m.romp !== "wsState" && m.romp !== "wsFail")) return;
      w.__labWs.push({ romp: m.romp, app: m.app, state: m.state || "", t: Date.now() });
    });
    let real;
    Object.defineProperty(w, "__rompNotify", { configurable: true, get: () => real, set: (f) => {
      real = typeof f !== "function" ? f : function (kind, text) { try { w.__labNotify.push({ kind: String(kind), text: String(text), t: Date.now() }); } catch (e) { /* recording only */ } return f.apply(this, arguments); };
    } });
    const watch = () => {
      const el = document.getElementById("merr");
      if (!el) return;
      const read = () => { const n = el.querySelector(".rerr-n"); const c = { has: el.classList.contains("has"), digit: n ? n.textContent : null, t: Date.now() }; const p = w.__labCue[w.__labCue.length - 1]; if (!p || p.has !== c.has || p.digit !== c.digit) w.__labCue.push(c); };
      read();
      new MutationObserver(read).observe(el, { attributes: true, attributeFilter: ["class"], subtree: true, characterData: true, childList: true });
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", watch); else watch();
  }
  return true;
};
await page.addInitScript(install);
const ensureInstalled = async () => {
  const late = [];
  for (const f of page.frames()) { try { if (await f.evaluate(install)) late.push(f.url()); } catch (e) { late.push("ERR:" + String(e).slice(0, 80)); } }
  return late;
};
const flip = (hidden) => page.evaluate((h) => {
  const docs = [window].concat(Array.from(window.frames));
  const done = [];
  for (const f of docs) {
    try { f.__labHidden = h; f.document.dispatchEvent(new f.Event("visibilitychange")); done.push(f.location.pathname); }
    catch (e) { done.push("ERR:" + String(e).slice(0, 80)); }
  }
  return done;
}, hidden);
// the Log as the person would find it: every entry (kind, text, unread, repeat count), the unread count the triangle draws,
// the control's digit and red cue, and whether the control is on screen in this layout
const readLog = () => page.evaluate(() => {
  let notes = [];
  try { notes = JSON.parse(localStorage.getItem("romp:notices") || "[]"); } catch (e) { notes = ["UNREADABLE"]; }
  const el = document.getElementById("merr"), n = el && el.querySelector(".rerr-n");
  return { t: Date.now(), entries: notes.map((x) => ({ kind: x.kind, text: x.text, seen: !!x.seen, n: x.n || 1 })),
           digit: n ? n.textContent : null, has: !!(el && el.classList.contains("has")),
           controlShown: !!(el && el.getClientRects().length && getComputedStyle(el).visibility !== "hidden"),
           link: (window.__rompLink && window.__rompLink()) ? window.__rompLink().up : null };
});
const wsNow = () => page.evaluate(() => { const s = {}; for (const w of window.__labWs || []) if (w.romp === "wsState") s[w.app] = w.state; return s; });
const waitUp = async (sinceT, ms) => {
  const deadline = now() + ms;
  while (now() < deadline) {
    const r = await page.evaluate((t) => { const s = {}; for (const w of window.__labWs || []) if (w.romp === "wsState" && w.t >= t) s[w.app] = w.state; return { s, link: !!(window.__rompLink && window.__rompLink().up) }; }, sinceT);
    if (r.link && EAGER.every((a) => r.s[a] === "up")) return true;
    await sleep(100);
  }
  return false;
};

try {
  out.t.load = now();
  await page.goto(cfg.url, { waitUntil: "load", timeout: 40000 });
  const booted = await waitUp(0, cfg.bootTimeoutMs || 30000);
  out.t.bootUp = now();
  out.bootUp = booted;
  out.wsAtBoot = await wsNow();
  if (!booted) await result({ died: "boot: not every eager pane and the link said up: " + JSON.stringify(out.wsAtBoot) });
  out.bodyClass = await page.evaluate(() => document.body.className);
  out.mobileShell = await page.evaluate(() => !!(window.__rompMobileOn && window.__rompMobileOn()));
  await sleep(cfg.settleMs || 1500);
  out.lateInstall = await ensureInstalled();
  out.installed = await page.evaluate(() => [window].concat(Array.from(window.frames)).map((f) => { try { return ((f === window ? "top" : (f.frameElement && f.frameElement.id)) || f.location.pathname) + (f.document.__labInit ? "" : ":MISSING"); } catch (e) { return "ERR"; } }));
  // the person reads the Log once before leaving: whatever the boot logged (the lab kernel has no Agent SDK, so its sdk entry)
  // is seen from here, the digit is the triangle's own glyph and the red cue is down, so a return's entry shows as the one unread
  out.logBeforeRead = await readLog();
  await page.evaluate(() => { window.__rompOpenErrs(); window.__rompCloseErrs(); });
  out.logAtBoot = await readLog();

  // --- the suspend ---
  state.phase = "suspended";
  if (cfg.regime === "slow") state.slow = true;
  else if (cfg.regime !== "healthy") { outageEnded = new Promise((r) => { endOutage = r; }); state.outage = true; }
  out.t.suspend = now();
  await flip(true);
  const closeHeld = async (panesFirst) => {
    let held = Array.from(live);
    if (panesFirst) held = held.filter((ws) => liveApp.get(ws) !== "shell").concat(held.filter((ws) => liveApp.get(ws) === "shell"));
    for (const ws of held) { live.delete(ws); try { await ws.close({ code: 1001, reason: "lab-suspend" }); } catch (e) { /* gone */ } }
    return held.length;
  };
  if (cfg.fin === "suspend") out.closedAtSuspend = await closeHeld();
  await sleep(cfg.hiddenDwellMs || 400);

  // --- the return ---
  state.phase = "returned";
  out.t.return = now();
  out.visibleDispatch = await flip(false);
  if (cfg.fin === "return" || cfg.fin === "return-panes-first") out.closedAtReturn = await closeHeld(cfg.fin === "return-panes-first");
  if (cfg.regime === "healthy" || cfg.regime === "slow") {
    out.upAfterReturn = await waitUp(out.t.return, cfg.upTimeoutMs || 15000);
    out.t.up = now();
  } else {
    // the outage holds; the Log is read at cfg.readsMs (ms from the return) while it stands, then the outage ends
    out.reads = [];
    for (const at of cfg.readsMs || []) { await sleep(Math.max(0, out.t.return + at - now())); out.reads.push({ at, log: await readLog(), ws: await wsNow() }); }
    await sleep(Math.max(0, out.t.return + cfg.outageMs - now()));
    state.outage = false;
    out.t.outageEnd = now();
    if (endOutage) endOutage();
    out.upAfterReturn = await waitUp(out.t.outageEnd, cfg.upTimeoutMs || 25000);
    out.t.up = now();
  }
  await sleep(cfg.afterMs || 2000);   // anything the return still had to say lands in this window
  out.logAfter = await readLog();
  out.t.done = now();
  out.notify = await page.evaluate(() => window.__labNotify || []);
  out.cue = await page.evaluate(() => window.__labCue || []);
  out.ws = await page.evaluate(() => window.__labWs || []);
  await result({});
} catch (e) {
  await result({ died: String(e).slice(0, 600) });
}
