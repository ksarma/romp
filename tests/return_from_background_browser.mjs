// The browser driver for tests/test_return_from_background_served.py: the phone-emulated background-and-return leg
// against a hermetic lab kernel. Opens the served dashboard shell in a playwright browser (Chromium; Firefox and WebKit
// as optional legs), waits for every pane socket to open, then emulates a suspend, an outage on the WebSocket path, a
// return from the background and the outage's end, and reads what the shim, the shell and the kernel recorded.
//
// The emulation, frame by frame (the repo dispatches no lifecycle event in a browser today, so this is new here):
//   * document.visibilityState and document.hidden are overridden in every document (an init script installs the
//     getters before any page script) to read a per-document flag; the driver flips the flag and dispatches
//     `visibilitychange` in the top document and then every same-origin frame, in one task from the top document,
//     recording the order in which the documents' handlers ran (top.__labVis).
//   * every WebSocket dial the page makes is routed (page.routeWebSocket on /ws): outside the outage the route passes
//     the dial through to the lab kernel and the driver keeps the route; at the suspend the driver closes every route it
//     holds (code 1001, the OS or the kernel's dead-socket drop, emulated) and the outage begins; during the outage a new
//     dial is REFUSED (the route closes it at once, never connecting) or HUNG (the route handler awaits the outage's end,
//     so the page-side socket stays CONNECTING: playwright opens the page side only once the handler settles, and a dial
//     the page cut while it hung is never connected afterwards, which would open a socket to the kernel that no page holds).
//   * the return: the flag flips to visible and `visibilitychange` is dispatched the same way. No `pageshow`: the design
//     dispatches none (iOS fires it on a back-forward navigation, not on a return from the background).
//   * scripts keep running while the documents read hidden, which a suspended phone's do not: the hidden dwell is short
//     (cfg.hiddenDwellMs) so the closes land as the FIN a thawed tab receives, and the timers the closes arm are still
//     pending at the return.
// Prints one compact `RESULT:` JSON line and writes the full result (every dial's record) to cfg.resultPath; exits 3 when
// the browser does not launch (the Python side turns that into a skip).
// Never touches a live kernel: cfg.healthz names the LAB port and is asserted before any request. Synthetic sessions only.
import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";

const require = createRequire(process.env.EXT_PKG);
const playwright = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
const engine = cfg.engine || "chromium";
const APPS = cfg.apps || ["chat", "timeline", "fleet", "feed", "waiting", "files"];
// the panes whose documents the shell loads at boot (stage 0, 2026-09-18: on the phone the Outline, the Sessions band and the
// Waiting pane load on their first tap, so their iframes sit at about:blank with no shim and no socket; the desktop loads all six)
const EAGER = cfg.eagerApps || APPS;
const FRESH_APPS = cfg.freshApps || APPS.filter((a) => a !== "files");   // the Files pane gets no resync frame, so it never files return-fresh
// a derived set that came out empty would end the boot wait and the fresh wait at once with nothing witnessed (review round 2,
// 2026-09-19: every derived expectation must fail when the derivation yields nothing), so the driver refuses it
if (!EAGER.length || !FRESH_APPS.length) { console.error("empty eager or fresh set in cfg: " + JSON.stringify({ eager: EAGER, fresh: FRESH_APPS })); process.exit(5); }
const now = () => Date.now();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = { engine, shell: cfg.shell, regime: cfg.regime, outageMs: cfg.outageMs, hiddenDwellMs: cfg.hiddenDwellMs,
              t: {}, dials: [], errors: [], notes: [] };

// the lab port answers /healthz before anything is asked of it (a lab that never came up must not send a single request
// anywhere else; the live kernel's port is never named in cfg)
const healthz = await new Promise((resolve) => {
  const req = http.get(cfg.healthz, (res) => { res.resume(); resolve({ status: res.statusCode, boot: res.headers["x-romp-boot"] || null }); });
  req.on("error", (e) => resolve({ status: 0, error: String(e) }));
  req.setTimeout(5000, () => { req.destroy(); resolve({ status: 0, error: "timeout" }); });
});
if (healthz.status !== 200) { console.error("lab kernel not healthy: " + JSON.stringify(healthz)); process.exit(4); }
out.healthz = healthz;

let browser;
try { browser = await playwright[engine].launch(cfg.launch || {}); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }

// the full result (every dial's record: hundreds in the refused regime) goes to cfg.resultPath; the RESULT: line stays
// compact, since one writeSync to a pipe delivers 64 KiB and the rest is lost (the desktop refused leg, first run)
const result = async (extra) => {
  Object.assign(out, extra || {});
  if (cfg.resultPath) { try { fs.writeFileSync(cfg.resultPath, JSON.stringify(out)); } catch (e) { out.resultWriteError = String(e).slice(0, 200); } }
  const compact = { ...out, dials: undefined, dialsN: out.dials.length, wsWords: undefined, vis: undefined, resultPath: cfg.resultPath || null };
  fs.writeSync(1, "RESULT:" + JSON.stringify(compact) + "\n");
  try { await browser.close(); } catch (e) { /* closing */ }
  process.exit(0);
};
const die = (why) => result({ died: why });

// the two shells: a phone (an iPhone descriptor, the viewport the design names: under _MOBILE_MQ's 820 px, so the shell
// loads six pane iframes with one .m-on) and a desktop window
let ctxOpts;
if (cfg.shell === "phone") {
  const dev = { ...(playwright.devices["iPhone 14"] || {}) };
  delete dev.defaultBrowserType;
  ctxOpts = { ...dev, viewport: { width: 390, height: 844 } };
  if (engine === "firefox") { delete ctxOpts.isMobile; }   // playwright: isMobile is not supported in Firefox
} else {
  ctxOpts = { viewport: { width: 1600, height: 760 } };
}
const context = await browser.newContext(ctxOpts);
const page = await context.newPage();
page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });

// --- the routed WebSocket path: pass-through, then the outage regime ---
const state = { outage: false, phase: "boot" };
let outageEnded = null, endOutage = null;
const armOutage = () => { outageEnded = new Promise((r) => { endOutage = r; }); };
const live = new Set();   // routes passed through and still open, to close at the suspend
const appOf = (u) => { try { const q = new URL(u).searchParams; return q.get("app") || (/\/remote\//.test(u) ? "relay" : "?"); } catch (e) { return "?"; } };
const relayOf = (u) => { const m = /\/remote\/([^/]+)\/ws/.exec(u); return m ? m[1] : null; };
// THE HELD FULL (review round 3, 2026-09-19, fresh-2): on the BOOT chat dial, when cfg.holdActiveFullMs is set, every server frame
// naming the active tab (its `session` full and any tail with its id) is queued instead of forwarded, in order, while every other
// frame (the strip with its skeleton list, the statuses, the caps frame) goes through at once; after the hold the queue flushes in
// order. That makes the start gate's claim testable CAUSALLY in a real engine: the chain is armed by the strip's first paint and the
// chat is on screen, so the only thing holding the first background ask is the gate, and a prefetch stamped before the release left
// ahead of the active tab's full. The stamps are the proxy's (wire time), so no page-side apply time is needed.
let heldBootChat = false;   // one boot chat dial is held (a redial after the return is not: the return hold owns that half)
const wire = (ws, d) => {
  const server = ws.connectToServer();
  d.connectedT = now();
  const hold = cfg.holdActiveFullMs > 0 && cfg.activeSid && d.app === "chat" && d.phase === "boot" && !heldBootChat;
  if (hold) heldBootChat = true;
  const queue = []; let released = !hold;
  const names = (m) => { if (typeof m !== "string" || m.indexOf(cfg.activeSid) < 0) return false; try { const o = JSON.parse(m); return !!o && o.id === cfg.activeSid; } catch (e) { return false; } };
  server.onMessage((m) => { if (!d.firstServerMsgT) d.firstServerMsgT = now(); d.serverFrames = (d.serverFrames || 0) + 1;
    if (!released && names(m)) {
      if (!d.held) { d.held = { t: now(), id: cfg.activeSid }; setTimeout(() => { released = true; d.heldRelease = { t: now(), n: queue.length }; for (const q of queue) ws.send(q); queue.length = 0; }, cfg.holdActiveFullMs); }
      queue.push(m); return;
    }
    ws.send(m); });
  ws.onMessage((m) => { d.pageFrames = (d.pageFrames || 0) + 1; server.send(m);
    // the chat pane's asks for a full session frame (needFull, with its why): the idle prefetch's `prefetch`, the tap's `skeleton-click`
    try { if (typeof m === "string" && m.indexOf('"needFull"') >= 0) { const o = JSON.parse(m); if (o && o.type === "needFull") { (d.needFull = d.needFull || []).push(String(o.why || "")); (d.needFullT = d.needFullT || []).push({ why: String(o.why || ""), id: String(o.id || ""), t: now() }); } } } catch (e) { /* not JSON */ }
  });
  server.onClose((code, reason) => { d.serverClosedT = now(); d.serverCloseCode = code; live.delete(ws); try { ws.close({ code: code || 1000, reason: reason || "" }); } catch (e) { /* closed */ } });
  ws.onClose((code) => { d.pageClosedT = now(); d.pageCloseCode = code; live.delete(ws); try { server.close(); } catch (e) { /* closed */ } });
  live.add(ws);
};
await page.routeWebSocket((u) => /\/ws(\?|$)/.test(u.pathname + (u.search || "")), async (ws) => {
  const url = ws.url();
  const d = { n: out.dials.length, app: appOf(url), relay: relayOf(url), reconnect: /[?&]reconnect=1/.test(url), skeleton: /[?&]skeleton=1/.test(url), t: now(), phase: state.phase };   // skeleton: the diet's term (the phone's first chat dial, stage 0)
  out.dials.push(d);
  try {
    if (!state.outage) { d.verdict = "passed"; wire(ws, d); return; }
    if (cfg.regime === "refused") {
      d.verdict = "refused";
      await ws.close({ code: 1006, reason: "lab-refused" });   // closed at once, never connected: the page's onclose sees a dial that never opened
      return;
    }
    // hung: the handler stays pending, so the page-side socket stays CONNECTING until the outage ends. A cut by the page
    // (the shim's 15 s watchdog) reaches the route's page-close handler: complete it so the page gets its `close` event
    // (playwright's default chain would do the same by way of the absent server), and remember never to connect it.
    d.verdict = "hung";
    ws.onClose((code) => { d.cutByPage = true; d.cutT = now(); d.cutCode = code; try { ws.close({ code: code || 1000, reason: "lab-cut" }); } catch (e) { /* closed */ } });
    await outageEnded;
    if (d.cutByPage) { d.verdict = "hung-cut"; return; }
    d.verdict = "hung-released";
    wire(ws, d);
  } catch (e) {
    d.error = String(e).slice(0, 200);
  }
});

// --- the per-document install: the visibility override, the order recorder, the shell's wsState words, the beacon's
// switch. Registered as an init script (before any page script) AND re-run at boot in every frame the init script missed:
// the guard inside `install` is per document, so an iframe whose Window survives its navigation from about:blank (below)
// gets the override on the document that matters; the late pass is the backstop for any document the init script missed,
// since in a frame without the override the shim reads the browser's real visibilityState and the emulation is void there.
// A late install still drives the shim (it reads the getter at dispatch time); its recorder then runs after the shim's
// handler in that document, which changes nothing about the order across documents.
const install = (opts) => {
  const w = window;
  // the marker is the DOCUMENT's: an iframe navigating from its initial about:blank to a same-origin page keeps its Window
  // (the HTML spec's reuse; Firefox and WebKit every time, Chromium sometimes), so a marker on the window made the init
  // script's second run skip the new document, and the shim there read the browser's real visibilityState (first runs)
  if (document.__labInit) return false;
  document.__labInit = true;
  if (w.__labHidden === undefined) w.__labHidden = false;
  try {
    Object.defineProperty(document, "visibilityState", { get: () => (w.__labHidden ? "hidden" : "visible"), configurable: true });
    Object.defineProperty(document, "hidden", { get: () => !!w.__labHidden, configurable: true });
  } catch (e) { try { w.top.__labErrors = (w.top.__labErrors || []).concat(["override: " + e]); } catch (e2) { /* cross-origin */ } }
  // the order recorder: a capture listener, registered before any page script where the init script ran, so per document
  // it runs first; the record is kept on the top document so one read gives every document's stamp in dispatch order
  document.addEventListener("visibilitychange", () => {
    try {
      const T = w.top;
      const doc = location.href === "about:blank" ? "about:blank" : location.pathname;
      const id = w === T ? "top" : ((w.frameElement && w.frameElement.id) || "");
      (T.__labVis = T.__labVis || []).push({ doc, id, state: document.visibilityState, t: Date.now(), n: (T.__labVisN = (T.__labVisN || 0) + 1) });
    } catch (e) { /* cross-origin */ }
  }, true);
  // the feed pane's MODEL, read without painting it (review round 1, regression-3): the shim hands every local frame to
  // window.__rompFed.inbound, so the feed frame's facade is wrapped the moment federation.js publishes it (an accessor armed
  // before any page script; the pane's own registrations are untouched) and the last full feed frame's ask count is kept
  if (location.pathname === "/feed" && w.__rompFed === undefined && !w.__labFedHook) {
    w.__labFedHook = true; w.__labFeed = { asks: -1, fulls: 0, deltas: 0 };
    let real;
    Object.defineProperty(w, "__rompFed", { configurable: true, get: () => real, set: (v) => {
      real = v;
      if (v && typeof v.inbound === "function") { const orig = v.inbound; v.inbound = (h, m) => { try { if (m && m.type === "feed" && Array.isArray(m.asks)) { w.__labFeed.asks = m.asks.length; w.__labFeed.fulls++; } else if (m && m.type === "feedDelta") w.__labFeed.deltas++; } catch (e) { /* counting only */ } return orig(h, m); }; }
    } });
  }
  // the chat pane's session fulls, as delivered (review round 3, extra9-1): per id the event count of the last `session` frame, so a
  // leg can say whether a tab's full was heavy (render.ts defers a build with events to a rAF) or empty
  if (location.pathname === "/chat" && w.__rompFed === undefined && !w.__labChatHook) {
    w.__labChatHook = true; w.__labChat = { sessions: {} };
    let realC;
    Object.defineProperty(w, "__rompFed", { configurable: true, get: () => realC, set: (v) => {
      realC = v;
      if (v && typeof v.inbound === "function") { const orig = v.inbound; v.inbound = (h, m) => { try { if (m && m.type === "session" && m.id) w.__labChat.sessions[m.id] = Array.isArray(m.events) ? m.events.length : -1; } catch (e) { /* counting only */ } return orig(h, m); }; }
    } });
  }
  if (w === w.top && !w.__labTopInit) {
    w.__labTopInit = true;   // once per window: the shell's document is never replaced
    if (opts.bootTab) { try { localStorage.setItem("romp-mobile-tab", opts.bootTab); } catch (e) { /* no storage */ } }   // the tab the phone was left on (stage 0: the boot tab decides which panes load at boot)
    // the chat pane's persisted state blob (the shim's SK for the main column), with the session the phone was looking at: the dial's
    // active= hint. Without it the kernel keeps its fail-safe whole push for a page with no hint (no skeleton set, nothing to prefetch),
    // which is a first-ever open, not the measured phone's; a lab session id, synthetic
    if (opts.activeSid) { try { localStorage.setItem("romp-vscode-state-chat", JSON.stringify({ activeId: opts.activeSid })); } catch (e) { /* no storage */ } }
    w.__labWs = [];        // every {romp:'wsState',app,state} word a pane posted to the shell, stamped
    w.__labWsNow = {};     // the latest state per app
    w.addEventListener("message", (e) => {
      const m = e && e.data;
      if (!m || m.romp !== "wsState") return;
      w.__labWs.push({ app: m.app, state: m.state, t: Date.now() });
      w.__labWsNow[m.app] = m.state;
    });
    if (opts.perfShare || opts.showFilesControl) {
      // the beacon extension's opt-in (PR 762): the browser's timing rows carry vis, wsBytes, free and rafGap; read raw
      // from the store by the collector, so the literal true is what turns it on. showFilesControl (review round 3, extra9-2):
      // the gear's Files-control setting, the literal true under that key, so the shell's controller shows the Files tab and the
      // phone's show('files') does not fall to the chat; written before the shell parses, as an earlier visit would have left it
      try { const st = JSON.parse(localStorage.getItem("romp:settings") || "{}"); let dirty = false;
        if (opts.perfShare && st.perfShare !== true) { st.perfShare = true; dirty = true; }
        if (opts.showFilesControl && st.showFilesControl !== true) { st.showFilesControl = true; dirty = true; }
        if (dirty) localStorage.setItem("romp:settings", JSON.stringify(st)); } catch (e) { /* no storage */ }
    }
  }
  return true;
};
const installOpts = { perfShare: !!cfg.perfShare, bootTab: cfg.bootTab || "", activeSid: cfg.activeSid || "", showFilesControl: !!cfg.showFilesControl };
await page.addInitScript(install, installOpts);
// the frames the init script missed, installed late (before the suspend); recorded so the note knows which engine needed it
const ensureInstalled = async () => {
  const late = [];
  for (const f of page.frames()) {
    try {
      const did = await f.evaluate(install, installOpts);
      if (did) { let id = ""; try { id = await f.evaluate(() => (window.frameElement && window.frameElement.id) || (window === window.top ? "top" : "")); } catch (e) { /* detached */ } late.push(id || f.url()); }
    } catch (e) { late.push("ERR:" + String(e).slice(0, 80)); }
  }
  return late;
};

// one task from the top document: flip every document's flag and dispatch `visibilitychange` in each, top first then the
// frames in tree order (the browser's own order is what the recorder is for; the emulation has to pick one)
const flip = (hidden) => page.evaluate((h) => {
  const docs = [window].concat(Array.from(window.frames));
  const done = [];
  for (const f of docs) {
    try { f.__labHidden = h; f.document.dispatchEvent(new f.Event("visibilitychange")); done.push(f.location.pathname); }
    catch (e) { done.push("ERR:" + String(e).slice(0, 80)); }
  }
  return done;
}, hidden);

const readDiag = () => {
  let txt = "";
  try { txt = fs.readFileSync(cfg.diag, "utf8"); } catch (e) { return []; }
  const rows = [];
  for (const ln of txt.split("\n")) { if (!ln) continue; try { rows.push(JSON.parse(ln)); } catch (e) { /* a partial last line */ } }
  return rows;
};

try {
  out.t.load = now();
  await page.goto(cfg.url, { waitUntil: "load", timeout: 40000 });
  // every EAGER pane socket open: the shim posts {romp:'wsState',app,state:'up'} to the shell on each open; a lazy pane has no shim to post
  const bootDeadline = now() + (cfg.bootTimeoutMs || 30000);
  let up = {};
  while (now() < bootDeadline) {
    up = await page.evaluate(() => window.__labWsNow || {});
    if (EAGER.every((a) => up[a] === "up")) break;
    await sleep(150);
  }
  out.t.bootUp = now();
  out.bootUpApps = Object.keys(up).filter((a) => up[a] === "up").sort();
  out.bootMs = out.t.bootUp - out.t.load;
  out.wid = await page.evaluate(() => { try { return sessionStorage.getItem("romp:wid") || ""; } catch (e) { return ""; } });
  out.frames = page.frames().map((f) => { try { return new URL(f.url()).pathname; } catch (e) { return f.url(); } });
  out.bodyClass = await page.evaluate(() => document.body.className);
  out.mobileShell = await page.evaluate(() => !!document.getElementById("mtabs") && getComputedStyle(document.getElementById("mtabs")).display !== "none");
  await sleep(cfg.settleMs || 1500);   // the bundles' ready, the caps answer, the first pushes: the return is measured from a settled page
  // THE START GATE'S WITNESS (fresh-2): the boot chat dial's held full was released (the precondition happened); then the chain's first
  // prefetch after the release, within a bounded wait (the gate opened on the full, so the chain ran once it applied)
  if (cfg.holdActiveFullMs > 0) {
    const bootChat = out.dials.find((d) => d.app === "chat" && d.phase === "boot");
    const relDeadline = now() + 10000;
    while (now() < relDeadline && !(bootChat && bootChat.heldRelease)) await sleep(100);
    const pfDeadline = now() + 10000;
    const after = () => (bootChat && bootChat.heldRelease && (bootChat.needFullT || []).filter((x) => x.why === "prefetch" && x.t >= bootChat.heldRelease.t)) || [];
    while (now() < pfDeadline && !after().length) await sleep(100);
    out.gate = { held: bootChat ? bootChat.held || null : null, heldRelease: bootChat ? bootChat.heldRelease || null : null,
                 prefetchAfterReleaseMs: after().length && bootChat.heldRelease ? after()[0].t - bootChat.heldRelease.t : -1 };
  }
  // the chat strip after the settle (review round 3, extra9-1): which tab is active and which tabs are skeletons, read off the pane's DOM
  // (display:none behind another tab or not); the leg's stored tab is echoed so the check can compare
  out.activeSid = cfg.activeSid || "";
  out.chatSessions = await (async () => { const f = page.frames().find((fr) => { try { return new URL(fr.url()).pathname === "/chat"; } catch (e) { return false; } }); if (!f) return null; try { return await f.evaluate(() => (window.__labChat || {}).sessions || null); } catch (e) { return null; } })();
  out.chatStrip = await (async () => { const f = page.frames().find((fr) => { try { return new URL(fr.url()).pathname === "/chat"; } catch (e) { return false; } }); if (!f) return null;
    try { return await f.evaluate(() => Array.from(document.querySelectorAll("#tabs .tab[data-id]")).map((t) => ({ id: t.dataset.id, skeleton: t.classList.contains("tab-skeleton"), active: t.classList.contains("active") }))); } catch (e) { return null; } })();
  // the iframes' src after the settle: the lazy contract read off the DOM (a lazy pane has none until its tap; every eager pane has its page)
  out.srcAtBoot = await page.evaluate(() => Object.fromEntries(Array.from(document.querySelectorAll("iframe[id^=f-]")).map((f) => [f.id.slice(2), f.getAttribute("src")])));
  out.wsWordsAtBoot = await page.evaluate(() => (window.__labWs || []).map((w) => w.app));   // every pane that said anything before the tap or the suspend
  // THE FEED'S FIRST PAINT (review round 1, regression-3; 2026-09-19): the change's central paint decision witnessed in a real engine.
  // The feed frame's first frame is delivered (the shim stamps __rompPerfMarks.firstFrame) and applied; on the phone behind another
  // tab the board is NOT painted (zero [data-key] cards, the pane's own loader still up), and the Feed tab's first show paints it
  // (cards > 0, the loader retired); on the desktop, and on a phone opened on the Feed tab, the first frame paints on its own.
  const feedFrame = () => page.frames().find((f) => { try { return new URL(f.url()).pathname === "/feed"; } catch (e) { return false; } });
  // listChildren: #feed-list's children, the pane loader's own measure (a paint appends #feed-cols, or .feed-empty over an empty
  // model, and the loader retires on the first child), so "held" is read where the loader reads it (review round 2 closeout, D6: the
  // card count read 0 under a disabled hold too, the boot's empty-board paint having no cards); cards: the [data-key] elements
  // render() stamped, a shape check beside it; modelCards: the asks the last full feed frame handed to the pane carried (the
  // install's wrap of __rompFed.inbound, above), so "held" is a model with cards over a list with no child, never a list that is
  // empty because nothing has arrived
  const feedRead = () => { const f = feedFrame(); return f ? f.evaluate(() => ({ cards: document.querySelectorAll("#feed-list [data-key]").length, listChildren: (function () { const l = document.getElementById("feed-list"); return l ? l.childElementCount : -1; })(), firstFrame: (window.__rompPerfMarks || {}).firstFrame, spinGone: !!(document.getElementById("pane-spin") && document.getElementById("pane-spin").classList.contains("gone")),
    modelCards: (window.__labFeed || {}).asks === undefined ? -1 : window.__labFeed.asks, feedFrames: { fulls: (window.__labFeed || {}).fulls, deltas: (window.__labFeed || {}).deltas } })).catch(() => null) : Promise.resolve(null); };
  {
    const feedDeadline = now() + 15000;
    let fr = null;
    while (now() < feedDeadline) {   // until the feed's model HOLDS cards (a read before it would say 0 for nothing)
      fr = await feedRead();
      if (fr && fr.firstFrame !== undefined && fr.modelCards > 0 && (cfg.shell === "phone" && cfg.bootTab !== "feed" ? true : fr.cards > 0)) break;
      await sleep(150);
    }
    out.feedBeforeShow = fr;
    if (cfg.shell === "phone" && cfg.bootTab !== "feed") {
      await sleep(300);   // the hold is a standing state: a beat after the delivery the board is still unpainted
      out.feedBeforeShow = await feedRead();
      out.t.feedShow = now();
      await page.click("#mtabs button[data-pane=feed]");   // the Feed tab's first show
      const showDeadline = now() + 15000;
      let after = null;
      while (now() < showDeadline) { after = await feedRead(); if (after && after.cards > 0 && after.spinGone) break; await sleep(100); }
      out.feedAfterShow = { ...(after || {}), ms: after && after.cards > 0 ? now() - out.t.feedShow : -1 };
      await page.click("#mtabs button[data-pane=" + (cfg.bootTab || "chat") + "]");   // back to the boot tab (a Feed show-and-hide: the feed is exempt from parking, so the parked set below is unchanged)
      await sleep(300);
    }
  }
  // THE SHELL LOADER PAINTS (review round 1, ui-2): armed BEFORE the tap, an observer on the body's class list records the loader's
  // computed style and box the moment `pane-loading` is added (the socket comes up ~170 ms after the tap, so a read after it races)
  if (cfg.tapPane) await page.evaluate(() => {
    window.__labLoaderSeen = null;
    new MutationObserver(() => {
      if (window.__labLoaderSeen || !document.body.classList.contains("pane-loading")) return;
      const el = document.getElementById("pane-load"), bar = document.getElementById("mtabs");
      const r = el.getBoundingClientRect(), b = bar.getBoundingClientRect();
      window.__labLoaderSeen = { display: getComputedStyle(el).display, loaderDisplay: getComputedStyle(el.querySelector(".rl-in")).display, height: r.height, bottom: r.bottom, barTop: b.top, t: Date.now() };
    }).observe(document.body, { attributes: true, attributeFilter: ["class"] });
  });
  // the TAB-TAP leg (stage 0): tap a lazy pane's tab, wait for its socket (its document loads on the tap), then go back to the chat,
  // so the return below finds a tapped pane off screen: the parked-pane contract (D2) exercised on a pane that did not exist at boot
  if (cfg.tapPane) {
    const prefetchBeforeTap = out.dials.filter((d) => d.app === "chat").reduce((n, d) => n + (d.needFull || []).filter((w) => w === "prefetch").length, 0);
    out.t.tap = now();
    if (cfg.abortPane) {
      // HIGH 2 (review round 1, 2026-09-19): the tapped pane's document fetch FAILS at the first tap (the route aborts the navigation).
      // Chromium commits an error page and fires load; Firefox and WebKit keep about:blank with no load event the shell can act on,
      // so the shell's 30 s backstop is their detector (the wait below outlasts it). The shell must re-park the pane, say so where the user looks
      // (body.pane-failed, #pane-load painted with the message, the loader itself down) and load it on the re-tap.
      const abortPath = "/" + cfg.abortPane;
      const isAbortUrl = (u) => u.pathname === abortPath;
      // abortMode error-body (HIGH 2, review round 2 closeout): the fetch answers a 502 with a body, a proxy's page while the kernel
      // restarts: same-origin at the pane's url, committed, and load fires in every engine; the shell must not take it for the pane's
      // own document (the pane shim's window marker tells them apart), so the failed state, the re-park and the re-tap are the same
      const aborter = cfg.abortMode === "error-body"
        ? (route) => route.fulfill({ status: 502, contentType: "text/html", body: "<!DOCTYPE html><html><body><h1>502 Bad Gateway</h1></body></html>" })
        : (route) => route.abort();
      await page.route(isAbortUrl, aborter);
      await page.click("#mtabs button[data-pane=" + cfg.tapPane + "]");
      const failDeadline = now() + 45000;
      let failedSeen = null;
      while (now() < failDeadline) {
        failedSeen = await page.evaluate((pane) => {
          if (!document.body.classList.contains("pane-failed")) return null;
          const el = document.getElementById("pane-load"), f = document.getElementById("f-" + pane);
          return { display: getComputedStyle(el).display, loaderDisplay: getComputedStyle(el.querySelector(".rl-in")).display,
                   msg: (document.getElementById("pane-load-msg") || {}).textContent || "", src: f.getAttribute("src"), lazy: f.getAttribute("data-lazy-src"),
                   loading: document.body.classList.contains("pane-loading") };
        }, cfg.abortPane);
        if (failedSeen) break;
        await sleep(200);
      }
      out.abort = { ms: failedSeen ? now() - out.t.tap : -1, mode: cfg.abortMode || "abort", ...(failedSeen || {}) };
      await page.unroute(isAbortUrl, aborter);
      out.t.retap = now();
      await page.click("#mtabs button[data-pane=" + cfg.tapPane + "]");   // the re-tap: the shell promotes the re-parked pane again, as a first tap would
    } else {
      await page.click("#mtabs button[data-pane=" + cfg.tapPane + "]");
    }
    const tapDeadline = now() + (cfg.bootTimeoutMs || 30000);
    let tapUp = {};
    while (now() < tapDeadline) {
      tapUp = await page.evaluate(() => window.__labWsNow || {});
      if (tapUp[cfg.tapPane] === "up") break;
      await sleep(100);
    }
    out.t.tapUp = now();
    out.tapUpMs = tapUp[cfg.tapPane] === "up" ? out.t.tapUp - (out.t.retap || out.t.tap) : -1;   // from the tap that loaded it (the re-tap, under abortPane)
    // the loading state RETIRES on the iframe's load event, which for a pane whose bundle is large (waiting.js, files.js: about 300 KB
    // each) comes AFTER its shim's socket is up (the inline shim dials at parse, the load event waits for the bundle): wait for the
    // retirement, bounded, and stamp it from the tap (review round 3, extra9-2; the Outline's small bundle had always loaded first)
    const clearDeadline = now() + (cfg.bootTimeoutMs || 30000);
    let cleared = false;
    while (now() < clearDeadline) {
      cleared = await page.evaluate((p) => { const f = document.getElementById("f-" + p), d = f && f.parentElement; return !document.body.classList.contains("pane-loading") && !!d && !d.classList.contains("loading"); }, cfg.tapPane);
      if (cleared) break;
      await sleep(50);
    }
    out.loadingClearedMs = cleared ? now() - (out.t.retap || out.t.tap) : -1;
    out.loaderSeen = await page.evaluate(() => window.__labLoaderSeen || null);   // what the observer saw the moment the loader went up
    out.srcAfterTap = await page.evaluate(() => Object.fromEntries(Array.from(document.querySelectorAll("iframe[id^=f-]")).map((f) => [f.id.slice(2), f.getAttribute("src")])));
    out.loadingAfterTap = await page.evaluate(() => ({ body: document.body.classList.contains("pane-loading"), failed: document.body.classList.contains("pane-failed"), panes: Array.from(document.querySelectorAll(".pane.loading")).map((d) => d.id), failedPanes: Array.from(document.querySelectorAll(".pane.failed")).map((d) => d.id) }));
    await page.click("#mtabs button[data-pane=chat]");
    await sleep(Math.max(300, (cfg.settleMs || 1500) / 2));
    // the kernel's wsopen rows carry whole seconds and the measurement's return window opens one second early, so the tapped
    // pane's own socket must be at least two seconds old at the return or its boot dial reads as a dial AT the return (one
    // run of the full file counted it so, 1.3 s before the return; review round 1's build)
    await sleep(Math.max(0, 2500 - (now() - out.t.tapUp)));
    out.tapped = cfg.tapPane;
    // the chat pane's idle prefetch (stage 0, review round 1): a phone opened on another tab holds the chain while the chat is
    // display:none; the Chat tab's show re-arms it. Counted from the chat socket's needFull asks: none before the tap, one after
    if (cfg.expectPrefetchAfterChatTap) {
      const prefetchAsks = () => out.dials.filter((d) => d.app === "chat").reduce((n, d) => n + (d.needFull || []).filter((w) => w === "prefetch").length, 0);
      out.prefetchBeforeTap = prefetchBeforeTap;
      // the chat frame's visibility roads at the tap (extra9-1): its observer, and the published word (undefined: never published)
      out.chatVisibility = await (async () => { const f = page.frames().find((fr) => { try { return new URL(fr.url()).pathname === "/chat"; } catch (e) { return false; } }); if (!f) return null;
        try { return await f.evaluate(() => ({ observer: typeof IntersectionObserver, word: window.__rompPaneHidden === undefined ? "undefined" : String(window.__rompPaneHidden) })); } catch (e) { return null; } })();
      const pfDeadline = now() + (cfg.bootTimeoutMs || 30000);
      while (now() < pfDeadline && prefetchAsks() <= prefetchBeforeTap) await sleep(100);
      out.prefetchAfterChatTapMs = prefetchAsks() > prefetchBeforeTap ? now() - out.t.tap : -1;
    }
    out.framesAtBoot = out.frames;
    out.frames = page.frames().map((f) => { try { return new URL(f.url()).pathname; } catch (e) { return f.url(); } });   // the frames the page holds at the suspend: the tapped pane's document is one now
  }
  out.lateInstall = await ensureInstalled();
  out.installed = await page.evaluate(() => { const docs = [window].concat(Array.from(window.frames)); return docs.map((f) => { try { return ((f === window ? "top" : (f.frameElement && f.frameElement.id)) || f.location.pathname) + (f.document.__labInit ? "" : ":MISSING"); } catch (e) { return "ERR"; } }); });
  if (cfg.shots) await page.screenshot({ path: cfg.shots + "-boot.png" }).catch(() => {});

  // --- the suspend: hidden in every document, the outage armed, every held socket closed ---
  state.phase = "suspended";
  armOutage();
  state.outage = true;
  out.t.suspend = now();
  out.hiddenDispatch = await flip(true);
  const held = Array.from(live);
  out.closedAtSuspend = held.length;
  for (const ws of held) { live.delete(ws); try { await ws.close({ code: 1001, reason: "lab-suspend" }); } catch (e) { /* gone */ } }
  out.t.closed = now();
  await sleep(cfg.hiddenDwellMs || 400);

  // --- the return: visible in every document; the outage holds for cfg.outageMs from here ---
  state.phase = "returned";
  out.t.return = now();
  out.visibleDispatch = await flip(false);
  if (cfg.shots) page.screenshot({ path: cfg.shots + "-returned.png" }).catch(() => {});
  await sleep(Math.max(0, out.t.return + cfg.outageMs - now()));
  state.phase = "after";
  state.outage = false;
  out.t.outageEnd = now();
  endOutage();

  // --- fresh content: the shim files return-fresh on the first non-keepalive frame after a return; the rows reach the
  // kernel's client-diag.jsonl on the reopened socket. Wait for every pane that files one (FRESH_APPS), bounded.
  const tRetS = Math.floor(out.t.return / 1000) - 1;
  const freshDeadline = now() + (cfg.freshTimeoutMs || 25000);
  const freshSeen = {};
  let rows = [];
  while (now() < freshDeadline) {
    rows = readDiag();
    for (const r of rows) {
      if (r.wid !== out.wid || r.surface !== "pane-shim" || r.what !== "return-fresh" || r.t < tRetS) continue;
      const a = r.data && r.data.app;
      if (a && freshSeen[a] === undefined) freshSeen[a] = now() - out.t.outageEnd;
    }
    if (FRESH_APPS.every((a) => freshSeen[a] !== undefined)) break;
    await sleep(250);
  }
  out.freshSeenMsAfterOutage = freshSeen;   // wall clock at which the driver first saw each pane's row, from the outage's end
  out.t.fresh = now();
  await sleep(cfg.settleMs || 1500);       // wsconnfail rides the next open; the perf minute rows flush on their own clock
  // the chain after the return (the owner's answer, 2026-09-19): the chat's background asks (needFull why=prefetch) on the dials
  // made from the return on. On the phone the redial reloads the visible tab alone; the desktop's chain runs as before.
  out.prefetchAfterReturn = out.dials.filter((d) => d.app === "chat" && d.t >= out.t.return).reduce((n, d) => n + (d.needFull || []).filter((w) => w === "prefetch").length, 0);
  if (cfg.shots) await page.screenshot({ path: cfg.shots + "-fresh.png" }).catch(() => {});
  out.t.done = now();
  out.vis = await page.evaluate(() => window.__labVis || []);
  out.wsWords = await page.evaluate(() => window.__labWs || []);
  out.wsNow = await page.evaluate(() => window.__labWsNow || {});
  out.overrideErrors = await page.evaluate(() => window.__labErrors || []);
  out.liveAtEnd = live.size;
  await result({});
} catch (e) {
  await die(String(e).slice(0, 600));
}
