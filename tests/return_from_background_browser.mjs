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
  // leg can say whether a tab's full was heavy (render.ts defers a build with events to a rAF) or empty. Keyed on the frame ELEMENT, not
  // the document path: the chat iframe is parser-created (src in the served markup) and in Firefox the init script runs only in its
  // initial about:blank document, whose Window the /chat document keeps, so a path guard never matched there and the count read None
  // (the feed is promoted by script, so its document gets an init run of its own and the path guard above serves it)
  if (((w.frameElement && w.frameElement.id) === "f-chat" || location.pathname === "/chat") && w.__rompFed === undefined && !w.__labChatHook) {
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
  if (cfg.tapPane && cfg.abortMode === "unmarked") {
    // docState's `doc` answer in a REAL engine (pass 5, the author's label, 2026-09-20, taking the reviewer's round-4 finding tests-1: pass 3's served leg for the shown-as-served road was
    // deleted with the narrowing, and the node harness's hand-built documentElement was the answer's only driver). The tapped pane's document
    // request is re-issued to the lab kernel (route.fetch, the stored cookie riding as ever) and the frame is fulfilled with the kernel's own
    // 200, status and headers, its body with the inline shim's WHOLE <script> element removed, the one holding `window.__rompApp=APP;` (the
    // marker the shell reads for `app`; the author's pass-5 verify: with the one statement removed the shim still ran to its connect() and redialed
    // the kernel at ~250 ms, refused every time, a perturbation the prose denied). So the frame holds a document the kernel stamped
    // (data-romp-served=200 on its <html> tag, written by Handler._send) with no pane shim in its window, the shape of the kernel's "needs the
    // ui/ modules" page, through a real HTML parser; the bundles' <script src> elements stay, as the pane's own page carries them. The shell
    // must show it as served: the loader retires on the document's load (not the 30 s backstop), the src stays, no failed state on the body
    // or the pane, one pane-load-unmarked row via load and no pane-load-failed row. The stamp is read in the engine off documentElement (a
    // byte count cannot tell a stamped root tag from a stamped `<html` elsewhere in the body). No shim runs in the document, so the pane says
    // nothing on the shell's wire (no wsState word, no socket dial for its app after the tap; pinned off out.wsWords and out.dials): the tapUp
    // wait is skipped and out.tapped stays null, so _parked expects nothing parked at the return and _lazy counts a no-tap boot.
    const path = "/" + cfg.tapPane, isPath = (u) => u.pathname === path;
    const MARK = "window.__rompApp=APP;";
    const SHIM_SCRIPT = /<script\b[^>]*>(?:(?!<\/script>)[\s\S])*?window\.__rompApp=APP;(?:(?!<\/script>)[\s\S])*<\/script>/g;   // the inline <script> element that holds the marker statement: the shim's, whole
    const unmarked = { status: null, contentType: null, scripts: null, scriptsStripped: 0, stripped: 0, stampedTags: null };
    const stripper = async (route) => {
      const resp = await route.fetch();
      unmarked.status = resp.status(); unmarked.contentType = (resp.headers() || {})["content-type"] || null;
      const text = await resp.text();
      const shim = text.match(SHIM_SCRIPT) || [];
      unmarked.scripts = (text.match(/<script\b/g) || []).length;                      // the page's script elements before the strip (the shim's inline one, the bundles' src ones)
      unmarked.scriptsStripped += shim.length;                                         // exactly one element removed: the shim's
      unmarked.stripped += shim.join("").split(MARK).length - 1;                      // the marker statements inside it (one)
      const body = text.replace(SHIM_SCRIPT, "");
      unmarked.stampedTags = (body.match(/<html data-romp-served=200[\s>]/g) || []).length;   // the kernel's stamp survives the strip (counted, not read)
      return route.fulfill({ response: resp, body });
    };
    await page.route(isPath, stripper);
    out.t.tap = now();
    await page.click("#mtabs button[data-pane=" + cfg.tapPane + "]");
    const clearDeadline = now() + 20000;
    let cleared = false;
    while (now() < clearDeadline) {
      cleared = await page.evaluate((p) => { const f = document.getElementById("f-" + p), d = f && f.parentElement; return !document.body.classList.contains("pane-loading") && !!d && !d.classList.contains("loading"); }, cfg.tapPane);
      if (cleared) break;
      await sleep(50);
    }
    out.loadingClearedMs = cleared ? now() - out.t.tap : -1;
    out.loaderSeen = await page.evaluate(() => window.__labLoaderSeen || null);
    out.unmarked = await page.evaluate((p) => {
      const f = document.getElementById("f-" + p), d = f.parentElement;
      let url = null, stamp = null, shim = null;
      try { url = f.contentDocument ? f.contentDocument.URL : null; stamp = f.contentDocument && f.contentDocument.documentElement ? f.contentDocument.documentElement.getAttribute("data-romp-served") : null; shim = f.contentWindow ? typeof f.contentWindow.__rompApp : null; } catch (e) { url = "ERR:" + String(e).slice(0, 60); }
      return { src: f.getAttribute("src"), lazy: f.getAttribute("data-lazy-src"), bodyFailed: document.body.classList.contains("pane-failed"), bodyLoading: document.body.classList.contains("pane-loading"),
               divFailed: d.classList.contains("failed"), divLoading: d.classList.contains("loading"), url, stamp, shim, msg: (document.getElementById("pane-load-msg") || {}).textContent || "" };
    }, cfg.tapPane);
    out.unmarkedRoute = unmarked;
    await page.unroute(isPath, stripper);
    await page.click("#mtabs button[data-pane=chat]");
    await sleep(Math.max(300, (cfg.settleMs || 1500) / 2));
    out.tapped = null;   // no shim in the served document (its script element stripped whole): nothing to park, nothing to dial; the pins on out.dials and out.wsWords hold the premise
    out.framesAtBoot = out.frames;
    out.frames = page.frames().map((f) => { try { return new URL(f.url()).pathname; } catch (e) { return f.url(); } });
  } else if (cfg.tapPane) {
    const prefetchBeforeTap = out.dials.filter((d) => d.app === "chat").reduce((n, d) => n + (d.needFull || []).filter((w) => w === "prefetch").length, 0);
    // THE FIRST TAP'S WITNESS (review round 3, tests-1): the pane DOCUMENT's own load, stamped by a listener armed on the frame element BEFORE
    // the tap (a listener armed after the click can miss a fast origin's load), once the document is not the initial about:blank; re-armed
    // before an abort leg's re-tap, so the stamp is the loaded document's on every leg
    const armDocLoad = () => page.evaluate((p) => {
      const w = window; w.__labDocLoad = null;
      const f = document.getElementById("f-" + p);
      f.addEventListener("load", () => { let url = null; try { url = f.contentDocument ? f.contentDocument.URL : null; } catch (e) { url = "ERR"; } if (w.__labDocLoad === null && url && url !== "about:blank") w.__labDocLoad = { t: Date.now(), url }; }, { once: false });
      // the loading state's RETIREMENT, stamped by the page: a MutationObserver over the body's and the pane div's class lists records the
      // first moment the loading state it saw painted (body.pane-loading, or the pane div's `loading`) is gone. Armed here so a re-arm before
      // an abort leg's re-tap resets it: the failure's own retirement of the first promotion's loader is not the loaded document's
      w.__labLoadingRetired = null;
      if (w.__labLoadingObs) { try { w.__labLoadingObs.disconnect(); } catch (e) { /* an observer of an earlier arm */ } }
      const d = f.parentElement; let seen = false;
      const read = () => { const on = document.body.classList.contains("pane-loading") || !!(d && d.classList.contains("loading")); if (on) seen = true; else if (seen && w.__labLoadingRetired === null) w.__labLoadingRetired = { t: Date.now() }; };
      const obs = new MutationObserver(read);
      obs.observe(document.body, { attributes: true, attributeFilter: ["class"] });
      if (d) obs.observe(d, { attributes: true, attributeFilter: ["class"] });
      w.__labLoadingObs = obs;
    }, cfg.tapPane);
    await armDocLoad();
    out.t.tap = now();
    if (cfg.abortPane) {
      // HIGH 2 (review round 1, 2026-09-19): the tapped pane's document fetch FAILS at the first tap (the route aborts the navigation).
      // Chromium commits an error page and fires load; Firefox and WebKit keep about:blank with no load event the shell can act on,
      // so the shell's 30 s backstop is their detector (the wait below outlasts it). The shell must re-park the pane, say so where the user looks
      // (body.pane-failed, #pane-load painted with the message, the loader itself down) and load it on the re-tap.
      const abortPath = "/" + cfg.abortPane;
      const isAbortUrl = (u) => u.pathname === abortPath;
      // two failure inputs (cfg.abortMode). "abort": the route aborts the navigation (above). "denied" (review round 4, 2026-09-19, kernel-1 and
      // tests-1): the REAL kernel's own denial at the pane's url. The route re-issues the pane's own request to the lab kernel through
      // route.fetch with an EXPLICIT EMPTY Cookie header, which is the one form that keeps the context's stored cookie off the wire in every
      // engine (probed on all three: route.continue with the header deleted, and route.fetch with it deleted, both had the browser reattach
      // the stored cookie and the kernel answered 200), and fulfils the frame with that response: the kernel's own status, headers and bytes
      // (403, text/plain, a body that names the serve-token file's path), as it answers a token-gated route with no credential; the context's
      // cookie stays for every other request (the shell's socket and the eager panes ride it; round 3's leg fulfilled a hand-written body here
      // and called it the kernel's, so no test met the real one). The response's STATUS is recorded; its body is never read, printed or kept
      // by this driver: that path is the reason the shell must not show this document as content. The 403 commits a document and fires
      // load in every engine, so the load listener is its detector on all three (the abort's is the backstop off Chromium).
      const denied = { status: null, responses: 0 };
      const aborter = cfg.abortMode === "denied"
        ? async (route) => { const resp = await route.fetch({ headers: { ...route.request().headers(), cookie: "" } }); denied.responses++; denied.status = resp.status(); return route.fulfill({ response: resp }); }
        : (route) => route.abort();
      await page.route(isAbortUrl, aborter);
      await page.click("#mtabs button[data-pane=" + cfg.tapPane + "]");
      const failDeadline = now() + 45000;
      let failedSeen = null;
      while (now() < failDeadline) {
        failedSeen = await page.evaluate((pane) => {
          if (!document.body.classList.contains("pane-failed")) return null;
          const el = document.getElementById("pane-load"), f = document.getElementById("f-" + pane), btn = document.getElementById("pane-load-retry"), msgEl = document.getElementById("pane-load-msg");
          const er = el.getBoundingClientRect(), fr = f.getBoundingClientRect(), es = getComputedStyle(el);
          return { display: es.display, loaderDisplay: getComputedStyle(el.querySelector(".rl-in")).display,
                   msg: (msgEl || {}).textContent || "", src: f.getAttribute("src"), lazy: f.getAttribute("data-lazy-src"),
                   loading: document.body.classList.contains("pane-loading"),
                   // the overlay's paint over the pane (review round 4, the denied mode): its box, backdrop and stacking, and the frame's box under it,
                   // so the served test can say the pane's document is covered (never read: the geometry is the witness, not the text)
                   overlay: { bg: es.backgroundColor, position: es.position, zIndex: es.zIndex, top: er.top, bottom: er.bottom, left: er.left, right: er.right },
                   frame: { display: getComputedStyle(f).display, top: fr.top, bottom: fr.bottom, left: fr.left, right: fr.right },
                   // ui-1 (review round 3): the retry button in the failed state: painted, named, in the tab order; the message announced
                   retry: btn ? { display: getComputedStyle(btn).display, tabIndex: btn.tabIndex, hidden: btn.hidden, text: btn.textContent, role: msgEl ? msgEl.getAttribute("role") : null,
                                  focusable: (function () { try { btn.focus(); return document.activeElement === btn; } catch (e) { return false; } })() } : null };   // focusable: the element takes keyboard focus (focus() lands it), the witness every engine gives
        }, cfg.abortPane);
        if (failedSeen) break;
        await sleep(200);
      }
      const abortMs = failedSeen ? now() - out.t.tap : -1;   // to the failed state; the walk and the keyboard retry below are not its wait
      // the keyboard road (ui-1): from the body, Tab until the retry button is the active element (the overlay precedes the pane iframes in the
      // document, and the rail is display:none on the phone); recorded as the presses it took, -1 when twenty did not reach it, with the trail
      // of what each press focused (tag#id). Chromium and WebKit wrap through the document and reach it (10 presses in Chromium); playwright's
      // Firefox leaves the document for the browser chrome at the last focusable element and never wraps (probed on a synthetic page with the
      // overlay's CSS: Chromium's walk reads BODY then the overlay button, Firefox's stays on the bar's last button), so the served test asserts
      // the walk on the two engines that walk and the focus() witness above on all three
      let tabsToReach = -1; const tabTrail = [];
      if (failedSeen) {
        await page.evaluate(() => { try { document.activeElement && document.activeElement.blur && document.activeElement.blur(); } catch (e) { /* nothing focused */ } });
        for (let i = 1; i <= 20; i++) {
          await page.keyboard.press("Tab");
          const at = await page.evaluate(() => { const a = document.activeElement; return a ? a.tagName + "#" + (a.id || "") : "none"; });
          tabTrail.push(at);
          if (at === "BUTTON#pane-load-retry") { tabsToReach = i; break; }
        }
      }
      // ui-1 (review round 4, 2026-09-19): the keyboard's retry keeps its focus across the re-failure. Enter on the focused button runs its
      // click (the retry); paintLoading hides the button while the retry loads, which drops focus to the body in every engine, and the failed
      // paint that shows it again must put focus back, or the keyboard road survives one activation (round 3's leg pressed nothing). The route
      // still fails the fetch, so the second failure comes with the episode's second copy; read then: the active element and the button's
      // hidden state. Legs whose detector is the load listener (cfg.retryEnter: the Chromium abort leg, the denied legs), so the wait is the load's.
      let retryEnter = null;
      if (failedSeen && cfg.retryEnter) {
        await page.evaluate(() => { document.getElementById("pane-load-retry").focus(); });   // the keyboard's focus on the button (the walk above left it, or never reached it on Firefox)
        const t0 = now();
        await page.keyboard.press("Enter");
        const again = "Still not loading. Try again, or reload the page.";
        let seen = null;
        const dl = now() + 45000;
        while (now() < dl) {
          seen = await page.evaluate((again) => {
            const m = document.getElementById("pane-load-msg");
            if (!document.body.classList.contains("pane-failed") || !m || m.textContent !== again) return null;
            const a = document.activeElement, b = document.getElementById("pane-load-retry");
            return { active: a ? a.tagName + "#" + (a.id || "") : "none", hidden: b.hidden, msg: m.textContent };
          }, again);
          if (seen) break;
          await sleep(100);
        }
        retryEnter = { ms: seen ? now() - t0 : -1, ...(seen || {}) };
      }
      out.abort = { ms: abortMs, mode: cfg.abortMode || "abort", tabsToReach, tabTrail, ...(failedSeen || {}), ...(cfg.abortMode === "denied" ? { denied } : {}), ...(retryEnter ? { retryEnter } : {}) };
      await page.unroute(isAbortUrl, aborter);
      await armDocLoad();   // the re-tap's document is the one whose load is stamped
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
    // the stamps are read once the DOCUMENT has loaded (bounded), not once the loading state is gone: a shell that retires the state
    // before the load (the defect the retirement assertions refuse) would otherwise have the load stamp read before the event and the
    // test red on the load's absence instead of on the early retirement. A pane with its document at boot (the chat tap) loads nothing
    // on the tap, so nothing is waited for
    const lazyTap = !(out.srcAtBoot || {})[cfg.tapPane];
    const loadDeadline = now() + (lazyTap ? 15000 : 0);
    let docLoad = await page.evaluate(() => window.__labDocLoad || null);
    while (!docLoad && now() < loadDeadline) { await sleep(100); docLoad = await page.evaluate(() => window.__labDocLoad || null); }
    out.docLoadMs = docLoad ? docLoad.t - (out.t.retap || out.t.tap) : -1;   // the document's own load event, from the tap that loaded it
    out.docLoadUrl = docLoad ? docLoad.url : null;
    const retired = await page.evaluate(() => window.__labLoadingRetired || null);
    out.loadingRetiredMs = retired ? retired.t - (out.t.retap || out.t.tap) : -1;   // the page's stamp of the loading state's retirement (armDocLoad), from the same tap: comparable to docLoadMs to the millisecond
    // the pane PAINTED (tests-1): its own loader retired (#pane-spin.gone; the Files page carries none, null) and its app element has
    // children (fleet: #fleet-list, the sessions; waiting: #waiting-list, the rows or the empty line; files: #files-empty, the recent rows'
    // title), polled to a deadline from the tap that loaded it. A pane with its document at boot (the boot-on-Feed legs' chat tap) is shown,
    // not loaded, by the tap: no element to poll for and nothing to wait 15 s on (painted stays null; the test reads it for a lazy tap alone)
    const paintEl = { fleet: "fleet-list", waiting: "waiting-list", files: "files-empty", timeline: "host" }[cfg.tapPane] || null;
    const paneFrame = () => page.frames().find((fr) => { try { return new URL(fr.url()).pathname === "/" + cfg.tapPane; } catch (e) { return false; } });
    const paintDeadline = paintEl && lazyTap ? now() + 15000 : 0;
    let painted = null;
    while (now() < paintDeadline) {
      const fr = paneFrame();
      painted = fr ? await fr.evaluate((id) => { const sp = document.getElementById("pane-spin"), el = id ? document.getElementById(id) : null; return { spinGone: sp ? sp.classList.contains("gone") : null, el: id, count: el ? el.childElementCount : -1 }; }, paintEl).catch(() => null) : null;
      if (painted && painted.count > 0 && painted.spinGone !== false) break;
      await sleep(100);
    }
    out.painted = painted ? { ...painted, ms: painted.count > 0 && painted.spinGone !== false ? now() - (out.t.retap || out.t.tap) : -1 } : null;
    out.loaderSeen = await page.evaluate(() => window.__labLoaderSeen || null);   // what the observer saw the moment the loader went up
    out.srcAfterTap = await page.evaluate(() => Object.fromEntries(Array.from(document.querySelectorAll("iframe[id^=f-]")).map((f) => [f.id.slice(2), f.getAttribute("src")])));
    out.loadingAfterTap = await page.evaluate(() => ({ body: document.body.classList.contains("pane-loading"), failed: document.body.classList.contains("pane-failed"), panes: Array.from(document.querySelectorAll(".pane.loading")).map((d) => d.id), failedPanes: Array.from(document.querySelectorAll(".pane.failed")).map((d) => d.id),
      retryHidden: (function () { const b = document.getElementById("pane-load-retry"); return b ? b.hidden : null; })() }));
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
