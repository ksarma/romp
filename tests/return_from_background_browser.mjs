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
  const compact = { ...out, dials: undefined, dialsN: out.dials.length, wsWords: undefined, vis: undefined, cue: undefined, postTap: undefined, resultPath: cfg.resultPath || null };   // the cue's records (every painted frame's chrome) ride the full result alone
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
  // cfg.landscapeKeyboard (ruling 3 at 79dce614c, 2026-10-04): the same phone turned landscape with the keyboard up, 844 wide and
  // 200 tall, the view of round 1's rehearsed check (the coarse pointer keeps the phone's shell at that width)
  ctxOpts = { ...dev, viewport: cfg.landscapeKeyboard ? { width: 844, height: 200 } : { width: 390, height: 844 } };
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

// THE CUE'S FRAME RECORDER (iOS item 4, 2026-10-02), evaluated in one pane document: a requestAnimationFrame loop reads, once per
// frame, whether the corner badge (#pane-reconn) is painted on and its text (textContent, so a count written through innerHTML or a
// child node reads too), and records each change of either, so a class set and cleared inside one task never reads as painted; a
// listener stamps each romp:wsfresh (the event that clears the badge). `armed` keeps the badge's class at arming time (a pane off
// screen paints no frame, so its loop may not run before it is shown). Each record of a painted badge also carries its box and the
// box of every visible control in the pane's chrome, so the test can say the painted badge covers none of them (finding of
// 2026-10-02: at top:8px it hid the chat header's tag filter and + button, and the Outline's tag filter and search). The chrome is
// what stays put when the content scrolls: the document outside the pane's content container (the chat's transcript, the Outline's,
// the Feed's and the Waiting pane's lists), and, inside it, every sticky or fixed element and what it holds (round 1 of the review,
// 2026-10-03: the subagent viewer's sticky header and its pin, and the Feed's sticky column heads and their drag chips, sit inside
// the container, and the recorder skipped them). A control is a link, button, form field, label, summary, an element with a button
// role, an action (data-act), a tabindex or draggable=true, the strip's resize handle, or anything drawn with a pointer or grab
// cursor or one of CSS's resize cursors, the keywords that end in -resize (the Feed's drag chip and the chat's landing notice have
// their cursor and nothing else, and so has the composer's resize handle; ruling 3 at 79dce614c, 2026-10-04, the same rule as the
// loader's rctl). Each control's box is the part a
// person can see (round 2 of the review, 2026-10-03, correctness-1): cut by every ancestor whose overflow clips it, along its chain
// of containing blocks (a fixed control escapes every ancestor that is not its containing block, an absolute one the ancestors
// between it and its positioned containing block), so a tab the desktop strip scrolls out of view, or a pinned-notes row below that
// strip's cap, is not chrome; a control wholly clipped is listed apart (`hidden`, its unclipped box) when it reaches the badge's
// column, so a leg can show that such controls lay under the badge's first place. Each painted record also carries the content
// container's top (`ctop`) and the view's width (`vw`), from which the first place is read. While the badge is painted, a
// change to the page (a MutationObserver on the body) or to the badge's box adds a record to `moves` at the next frame, with the
// badge's box and the chrome then, so a control that appears under a painted badge (the landing notice shown during the wait) is
// measured as well as the badge's place at its paint.
// THE HOLD'S TIMER, as events (`hold`, in the order they ran in this document): the badge paints only from its hold's timer
// (_pane_spin's setTimeout(rpaint, RHOLD)), so the recorder wraps this window's setTimeout and logs each arm of a callback named
// rpaint ("arm") and each run of one ("fire", with whether the badge was on after it), beside each romp:wsfresh ("fresh"); every
// entry carries the frame count at that moment (`f`). The test decides from these events which outcome to expect: a hold that
// fired before the fresh frame with a frame drawn between them painted the badge; a fresh frame that came first cleared the
// hold, and nothing paints. Not from the time between the tap and the fresh frame against the nominal hold: under load the
// timer fires late, so a fresh frame past the nominal second can still beat it (the full sweep of 2026-10-02: 1015 ms, no
// paint, correctly). The wrapper changes no timer: it passes every call through, the hold's with its own delay.
const cueRec = () => {
  const w = window; if (w.__labCue) return "again";
  const b0 = document.getElementById("pane-reconn");
  const MOVES_CAP = 200;
  const c = w.__labCue = { badge: [], moves: [], movesCapped: false, fresh: [], hold: [], frames: 0, lastT: 0, armed: { t: Date.now(), on: !!(b0 && b0.classList.contains("on")) } };
  const st = w.setTimeout;
  w.setTimeout = function (fn, ms) {
    if (typeof fn !== "function" || fn.name !== "rpaint") return st.apply(w, arguments);
    c.hold.push({ k: "arm", t: Date.now(), f: c.frames, ms });
    const rest = Array.prototype.slice.call(arguments, 2);
    return st.call(w, function () { const r = fn.apply(this, rest); const b = document.getElementById("pane-reconn"); c.hold.push({ k: "fire", t: Date.now(), f: c.frames, on: !!(b && b.classList.contains("on")) }); return r; }, ms);
  };
  let last = null;
  const read = () => { const b = document.getElementById("pane-reconn"); return { on: !!(b && b.classList.contains("on") && getComputedStyle(b).display !== "none"), text: b ? b.textContent : null }; };
  const box = (el) => { const r = el.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; };
  // the pane's content container, the id each pane page hands _pane_spin: the chat's transcript, else the pane's list (<pane>-list)
  const content = document.getElementById(location.pathname === "/chat" ? "content" : location.pathname.slice(1) + "-list");
  const CONTROL = "button, a[href], [role=button], [data-act], input, textarea, select, [tabindex], #tabbar-resize, [draggable=true], summary, label";
  const CURSOR = /^(pointer|grab|grabbing|(n|e|s|w|ne|nw|se|sw|ew|ns|nesw|nwse|col|row)-resize)$/;
  // the part of an element's box its overflow ancestors leave in view, [left, top, width, height] rounded, or null when none is
  const seen = (el, cs) => {
    const r = el.getBoundingClientRect(); let l = r.left, t = r.top, rt = r.right, bt = r.bottom, pos = cs.position;
    for (let a = el.parentElement; a && a !== document.body && a !== document.documentElement; a = a.parentElement) {
      const s = getComputedStyle(a), ct = s.contain || "";
      const cb = s.transform !== "none" || s.filter !== "none" || s.perspective !== "none" || /paint|layout|strict|content/.test(ct) || /transform|perspective|filter/.test(s.willChange || "");
      if (pos === "fixed" && !cb) continue;
      if (pos === "absolute" && s.position === "static" && !cb) continue;
      let cx = s.overflowX !== "visible", cy = s.overflowY !== "visible";
      if (/paint|strict|content/.test(ct)) cx = cy = true;
      if ((cx || cy) && s.display !== "inline" && s.display !== "contents") {
        const q = a.getBoundingClientRect(), x0 = q.left + a.clientLeft, y0 = q.top + a.clientTop;
        if (cx) { l = Math.max(l, x0); rt = Math.min(rt, x0 + a.clientWidth); }
        if (cy) { t = Math.max(t, y0); bt = Math.min(bt, y0 + a.clientHeight); }
      }
      pos = s.position;
    }
    return rt > l && bt > t ? [Math.round(l), Math.round(t), Math.round(rt - l), Math.round(bt - t)] : null;
  };
  let hiddenNow = [];   // the controls the last chrome() read found wholly clipped, in the badge's column
  const chrome = () => {
    const out = [], hid = [], b = document.getElementById("pane-reconn"), stuck = [];
    // the badge's column: from its left edge, or from where its left edge is at the first place (8 px from the view's right) if that is further left
    const bb = b ? b.getBoundingClientRect() : null, colR = bb ? document.documentElement.clientWidth - 8 : 0, colL = bb ? Math.min(bb.left, colR - bb.width) : 0;
    for (const el of Array.from(document.body.getElementsByTagName("*"))) {
      if (el === b || (b && b.contains(el)) || el === content) continue;
      const cs = getComputedStyle(el);
      const within = !!content && content.contains(el);
      // inside the content container only what a sticky or fixed element holds stays put; the rest scrolls under the badge
      if (within && (cs.position === "sticky" || cs.position === "fixed")) stuck.push(el);
      if (within && !stuck.some((p) => p.contains(el))) continue;
      if (!el.matches(CONTROL) && !CURSOR.test(cs.cursor)) continue;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height || cs.visibility === "hidden" || cs.display === "none") continue;
      const cls = typeof el.className === "string" && el.className.trim() ? "." + el.className.trim().split(/\s+/)[0] : "";
      const name = el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + cls;
      const vis = seen(el, cs);
      if (!vis) { if (bb && r.right > colL && r.left < colR) hid.push({ el: name, box: box(el), inContent: within }); continue; }
      out.push({ el: name, label: (el.getAttribute("aria-label") || el.getAttribute("title") || el.textContent || "").trim().slice(0, 30), box: vis, inContent: within });
    }
    hiddenNow = hid;
    return out;
  };
  let dirty = false, lastBox = "", lastSig = "";
  const sig = (bx, ch) => JSON.stringify(bx) + JSON.stringify(ch.map((x) => x.box));
  try { new MutationObserver(() => { dirty = true; }).observe(document.body, { childList: true, subtree: true, attributes: true, characterData: true }); } catch (e) { /* no observer */ }
  // THE LOADER'S OWN FRAME (round 2 of the review, 2026-10-03, ruling C): while painted, the badge's watch places it from a
  // requestAnimationFrame callback (rframe) that a change to the page or a scroll registers. The loop's callback, registered a frame
  // earlier, runs before it in that frame, so its read saw the page changed and the badge not yet placed, a state no frame paints
  // (the landing notice leg read the badge over the notice, 24 percent, at f1a720ef2). So the recorder wraps requestAnimationFrame:
  // when the page registers a callback named rframe, a late read is registered right after it, and the loop leaves that frame's
  // move record to the late read. The badge's paint and clear are recorded by the loop as before (the paint places the badge in its
  // own task). The wrapper changes no callback: it passes every call through.
  let late = false;
  const raf = w.requestAnimationFrame;
  const moveRead = () => {
    // a move is recorded only while the badge is drawn (a pane hidden by another tab draws nothing: a zero box) and only when its
    // box or the chrome's boxes changed, so a page that keeps mutating without moving anything adds no record. At most MOVES_CAP
    // records are kept; a move past the cap sets movesCapped, which the test fails on (round 2 of the review, fresh-3: the cap
    // dropped every later painted state unread while the leg stayed green)
    const bb = box(document.getElementById("pane-reconn")), bx = JSON.stringify(bb);
    if (bb[2] && bb[3] && (dirty || bx !== lastBox)) { const ch = chrome(), sg = sig(bb, ch); if (sg !== lastSig) {
      if (c.moves.length < MOVES_CAP) c.moves.push({ t: Date.now(), on: true, box: bb, chrome: ch, hidden: hiddenNow, content: !!content, ctop: content ? Math.round(content.getBoundingClientRect().top) : null, vw: document.documentElement.clientWidth });
      else c.movesCapped = true;
      lastSig = sg; } }
    lastBox = bx; dirty = false;
  };
  const lateRead = () => { late = false; const v = read(); if (v.on && v.on + "|" + v.text === last) moveRead(); };
  w.requestAnimationFrame = function (fn) { const id = raf.apply(w, arguments); if (typeof fn === "function" && fn.name === "rframe" && !late) { late = true; raf.call(w, lateRead); } return id; };
  const loop = () => { c.frames++; c.lastT = Date.now(); const v = read(), k = v.on + "|" + v.text; if (k !== last) { const e = { t: c.lastT, on: v.on, text: v.text };
    if (v.on) { e.box = box(document.getElementById("pane-reconn")); e.chrome = chrome(); e.hidden = hiddenNow; e.content = !!content; e.ctop = content ? Math.round(content.getBoundingClientRect().top) : null; e.vw = document.documentElement.clientWidth; lastBox = JSON.stringify(e.box); lastSig = sig(e.box, e.chrome); }
    c.badge.push(e); last = k; dirty = false; }
    else if (v.on && !late) moveRead();
    raf.call(w, loop); };
  raf.call(w, loop);
  w.addEventListener("romp:wsfresh", () => { const t = Date.now(); c.fresh.push(t); c.hold.push({ k: "fresh", t, f: c.frames }); });
  return "armed";
};

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
    // ui/ modules" page, through a real HTML parser; the bundles' <script src> elements stay, as the pane's own page carries them, and so
    // do the page's other inline scripts (its loader's, and since main's fork PR #919 the page-key script Handler._send puts first in
    // every authorized page's head): the route counts the script elements before and after the strip, one fewer after. The shell
    // must show it as served: the loader retires on the document's load (not the 30 s backstop), the src stays, no failed state on the body
    // or the pane, and no pane-load row (the reviewer's round 7 dropped both rows with their keys). The stamp is read in the engine off documentElement (a
    // byte count cannot tell a stamped root tag from a stamped `<html` elsewhere in the body). No shim runs in the document, so the pane says
    // nothing on the shell's wire (no wsState word, no socket dial for its app after the tap; pinned off out.wsWords and out.dials): the tapUp
    // wait is skipped and out.tapped stays null, so _parked expects nothing parked at the return and _lazy counts a no-tap boot.
    const path = "/" + cfg.tapPane, isPath = (u) => u.pathname === path;
    const MARK = "window.__rompApp=APP;";
    const SHIM_SCRIPT = /<script\b[^>]*>(?:(?!<\/script>)[\s\S])*?window\.__rompApp=APP;(?:(?!<\/script>)[\s\S])*<\/script>/g;   // the inline <script> element that holds the marker statement: the shim's, whole
    const unmarked = { status: null, contentType: null, scripts: null, srcScripts: null, scriptsKept: null, srcKept: null, scriptsStripped: 0, stripped: 0, stampedTags: null };
    const stripper = async (route) => {
      const resp = await route.fetch();
      unmarked.status = resp.status(); unmarked.contentType = (resp.headers() || {})["content-type"] || null;
      const text = await resp.text();
      const shim = text.match(SHIM_SCRIPT) || [];
      unmarked.scripts = (text.match(/<script\b/g) || []).length;                      // the page's script elements before the strip (its inline ones, the shim's among them, the page-key script, the bundles' src ones)
      unmarked.srcScripts = (text.match(/<script\b[^>]*\ssrc=/g) || []).length;       // the bundles' src elements among them
      unmarked.scriptsStripped += shim.length;                                         // the elements the shim's pattern matched (one: the shim's)
      unmarked.stripped += shim.join("").split(MARK).length - 1;                      // the marker statements inside it (one)
      const body = text.replace(SHIM_SCRIPT, "");
      unmarked.stampedTags = (body.match(/<html data-romp-served=200[\s>]/g) || []).length;   // the kernel's stamp survives the strip (counted, not read)
      unmarked.scriptsKept = (body.match(/<script\b/g) || []).length;                 // the page's script elements after the strip (all but the shim's: one element removed in all)
      unmarked.srcKept = (body.match(/<script\b[^>]*\ssrc=/g) || []).length;         // the bundles' src elements after the strip (every one stays)
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
      // cookie stays for every other request (the shell's socket and the eager panes ride it; pass 3's leg fulfilled a hand-written body here
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
      // paint that shows it again must put focus back, or the keyboard road survives one activation (pass 3's leg pressed nothing). The route
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

  // THE RECONNECT CUE (iOS item 4, 2026-10-02): what the page shows from here on, read on the page's own clock and events. In
  // the visible chat's document a requestAnimationFrame loop reads, once per frame, whether the corner badge (#pane-reconn) is
  // painted on and records each change, so a class set and cleared inside one task never reads as painted; a listener stamps
  // each romp:wsfresh (the event that clears the badge). In the shell a MutationObserver over the Log panel records each change
  // of the cue's live line (#rerr-live: shown, and its text). Armed after the boot, any tap and the settle, before the suspend.
  out.t.cueArmed = now();
  // cfg.cueApp names the pane whose badge is read (the visible chat by default; the Feed for the desktop Feed leg)
  const cueApp = cfg.cueApp || "chat";
  const frameOf = (app) => page.frames().find((f) => { try { return new URL(f.url()).pathname === "/" + app; } catch (e) { return false; } });
  const cueChat = frameOf(cueApp);
  // THE SUBAGENT VIEWER (round 1 of the review, 2026-10-03): cfg.subView opens the viewer in the chat before the suspend, from the
  // open control on the active session's Agent head (the lab's `tests` session carries one synthetic agent), and waits for its
  // sticky header, so the badge paints over a chat whose list holds that header and its pin
  if (cfg.subView) {
    const cf = frameOf("chat");
    out.subView = cf ? await cf.evaluate(async () => {
      const wait = async (f) => { for (let i = 0; i < 100; i++) { const v = f(); if (v) return v; await new Promise((r) => setTimeout(r, 100)); } return null; };
      const open = await wait(() => document.querySelector(".tool-open-agent"));
      if (!open) return { opened: false };
      open.click();
      const head = await wait(() => document.getElementById("sub-head"));
      const pin = head && head.querySelector("[role=button]");
      return { opened: !!head, pin: !!pin };
    }).catch((e) => ({ err: String(e).slice(0, 120) })) : { err: "no-chat-frame" };
    await sleep(800);
  }
  // THE OVERFLOWING STRIPS (round 2 of the review, 2026-10-03, correctness-1): cfg.overflowStrip fills one of the chat's two strips
  // that scroll what does not fit out of view until it hides about 150 px of rows, which then lie over the transcript's top, where
  // the badge's first place is: "tabs" adds synthetic tabs (the strip's own .tab class, whose cursor is a pointer; each grows to fill
  // its row, so every row reaches the badge's column at the strip's right end) to the desktop tab strip (#tabs in #tabbar, capped at
  // 150 px), and "notes" fills the pinned-notes strip (#pinned-notes, capped at min(11em, 30vh))
  // with rows built as pinned-notes.ts builds them, each with its details and unpin buttons, and shows it. Synthetic labels only.
  // Read back: the strip's visible and scrolled heights and the rows it holds; the rows are counted again when the leg ends.
  const stripRows = (kind) => frameOf("chat").evaluate((k) => document.querySelectorAll(k === "tabs" ? ".lab-tab" : ".lab-note").length, kind).catch(() => -1);
  // THE LONG PINNED NOTE (ruling 3 at 79dce614c, 2026-10-04): cfg.pinnedNote shows the pinned-notes strip with one note whose text
  // wraps (a row built as pinned-notes.ts builds it, its details and unpin buttons included; synthetic text), so on the landscape
  // phone with the keyboard up the list below it is shorter than the badge, and the composer's resize handle, over the list's
  // bottom edge, lies under the badge's first place. Read back: the strip's height, the list's top and height, the handle's box
  if (cfg.pinnedNote) {
    out.pinnedNote = await frameOf("chat").evaluate(() => {
      const mk = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; };
      const strip = document.getElementById("pinned-notes"), c = document.getElementById("content"), g = document.getElementById("composer-resize");
      if (!strip || !c) return { err: "no-strip" };
      strip.textContent = ""; strip.style.display = "";
      const item = mk("div", "pn-item pn-with-detail lab-note"), line = mk("div", "pn-line");
      line.appendChild(mk("span", "pn-text", "notes-api: " + "the search index rebuild reads its weights from the config file and the tokenizer covers hyphens and quotes, ".repeat(2)));
      const more = mk("button", "ut-more", "details"); more.type = "button"; line.appendChild(more);
      const un = mk("button", "pn-unpin", "unpin"); un.type = "button"; line.appendChild(un);
      item.appendChild(line); strip.appendChild(item);
      const r = c.getBoundingClientRect(), q = g ? g.getBoundingClientRect() : null;
      return { shown: true, noteH: Math.round(strip.getBoundingClientRect().height), list: [Math.round(r.top), Math.round(r.height)],
               handle: q ? [Math.round(q.left), Math.round(q.top), Math.round(q.width), Math.round(q.height)] : null, handleCursor: g ? getComputedStyle(g).cursor : null,
               vh: document.documentElement.clientHeight };
    }).catch((e) => ({ err: String(e).slice(0, 120) }));
    await sleep(600);
  }
  if (cfg.overflowStrip) {
    out.overflowStrip = await frameOf("chat").evaluate((kind) => {
      const mk = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; };
      const strip = document.getElementById(kind === "tabs" ? "tabbar" : "pinned-notes"), into = kind === "tabs" ? document.getElementById("tabs") : strip;
      if (!strip || !into) return { kind, err: "no-strip" };
      if (kind === "notes") { strip.textContent = ""; strip.style.display = ""; }
      for (let i = 0; i < 200 && strip.scrollHeight - strip.clientHeight < 150; i++) {
        if (kind === "tabs") { const t = mk("div", "tab lab-tab"); t.style.flexGrow = "1"; t.appendChild(mk("span", "", "notes-api-" + ["web", "api", "tests", "docs"][i % 4] + "-tokenizer-" + (10 + i))); into.appendChild(t); continue; }
        const item = mk("div", "pn-item pn-with-detail lab-note"), line = mk("div", "pn-line");
        line.appendChild(mk("span", "pn-text", "notes-api: check the tokenizer fixture " + (i + 1) + " before the rebuild"));
        const more = mk("button", "ut-more", "details"); more.type = "button"; line.appendChild(more);
        const un = mk("button", "pn-unpin", "unpin"); un.type = "button"; line.appendChild(un);
        item.appendChild(line); into.appendChild(item);
      }
      strip.scrollTop = 0;
      return { kind, clientH: strip.clientHeight, scrollH: strip.scrollHeight, rows: document.querySelectorAll(kind === "tabs" ? ".lab-tab" : ".lab-note").length };
    }, cfg.overflowStrip).catch((e) => ({ err: String(e).slice(0, 120) }));
    await sleep(600);
  }
  out.cueArm = {
    pane: cueChat ? await cueChat.evaluate(cueRec).catch((e) => "ERR:" + String(e).slice(0, 80)) : "no-pane-frame",
    shell: await page.evaluate(() => {
      const w = window; if (w.__labCueLog) return "again";
      const c = w.__labCueLog = [];
      let last = "";
      const read = () => { const el = document.getElementById("rerr-live"); return el ? { shown: el.style.display !== "none", text: (el.lastChild && el.lastChild.textContent) || "" } : { shown: false, text: "", absent: true }; };
      const rec = () => { const v = read(); const k = JSON.stringify(v); if (k !== last) { c.push(Object.assign({ t: Date.now() }, v)); last = k; } };
      const panel = document.getElementById("rerr-panel");
      if (!panel) return "no-panel";
      new MutationObserver(rec).observe(panel, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ["style"] });
      rec();
      return "armed";
    }).catch((e) => "ERR:" + String(e).slice(0, 80)),
  };

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
  // THE TAP AFTER THE RETURN (iOS item 4, findings of 2026-10-02): cfg.postTap names a pane the return parked (the pre-suspend tap
  // loaded it and went back to the chat, so it was off screen at the return). Started at the return's flip, so the tap can land
  // during an outage: at cfg.postTapMs after the return the driver arms the cue's frame recorder in that pane's document and taps
  // its tab, then waits for the pane's first fresh frame after the tap (the outage's length plus 15 s at most) and a hold past it
  // (cfg.cueHoldMs), so a badge the hold paints late is in the record too; then back to the chat. Awaited after the fresh wait.
  const postTapDone = !cfg.postTap ? null : (async () => {
    await sleep(Math.max(0, out.t.return + (cfg.postTapMs || 2000) - now()));
    const pf = page.frames().find((f) => { try { return new URL(f.url()).pathname === "/" + cfg.postTap; } catch (e) { return false; } });
    out.postTap = { pane: cfg.postTap, arm: pf ? await pf.evaluate(cueRec).catch((e) => "ERR:" + String(e).slice(0, 80)) : "no-frame" };
    out.t.postTap = now();
    await page.click("#mtabs button[data-pane=" + cfg.postTap + "]");
    const tapDeadline = now() + (cfg.outageMs || 0) + 15000;
    let rec = null;
    while (pf && now() < tapDeadline) {
      rec = await pf.evaluate(() => window.__labCue || null).catch(() => null);
      if (rec && rec.fresh.some((x) => x >= out.t.postTap)) break;
      await sleep(50);
    }
    await sleep((cfg.cueHoldMs || 1000) + 300);
    out.postTap.rec = pf ? await pf.evaluate(() => window.__labCue || null).catch((e) => ({ err: String(e).slice(0, 80) })) : null;
    out.t.postTapDone = now();
    await page.click("#mtabs button[data-pane=chat]");
  })().catch((e) => { out.postTapError = String(e).slice(0, 200); });
  // THE LANDING NOTICE OVER A PAINTED BADGE (round 1 of the review, 2026-10-03): cfg.noticeAfterPaint waits for the cue pane's badge
  // to paint, then shows the chat's landing notice (its on-demand hook, window.__rompLoadingPill, the real showLandingNotice) while
  // the outage holds, so a control appears under the painted badge. Started at the return's flip; awaited after the fresh wait.
  const noticeDone = !cfg.noticeAfterPaint ? null : (async () => {
    const deadline = now() + (cfg.outageMs || 0);
    while (now() < deadline) {
      const on = await cueChat.evaluate(() => { const c = window.__labCue; return !!(c && c.badge.length && c.badge[c.badge.length - 1].on); }).catch(() => false);
      if (on) break;
      await sleep(50);
    }
    await sleep(300);
    out.t.notice = now();
    out.notice = await frameOf("chat").evaluate(() => { if (typeof window.__rompLoadingPill !== "function") return { hook: false };
      window.__rompLoadingPill(true); const n = document.querySelector(".tx-landing-notice"); return { hook: true, shown: !!n && getComputedStyle(n).display !== "none" }; }).catch((e) => ({ err: String(e).slice(0, 120) }));
  })().catch((e) => { out.noticeError = String(e).slice(0, 200); });
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
  if (postTapDone) await postTapDone;   // the tap after the return (below the return's flip) finishes before the settle
  if (noticeDone) await noticeDone;
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
  out.cue = {   // the reconnect cue's record (iOS item 4): the chat's painted badge changes, its fresh stamps, its frame loop, the Log line's changes
    ...(cueChat ? await cueChat.evaluate(() => { const c = window.__labCue || {}; return { badge: c.badge || [], moves: c.moves || [], movesCapped: !!c.movesCapped, fresh: c.fresh || [], hold: c.hold || [], frames: c.frames || 0, lastT: c.lastT || 0 }; }).catch((e) => ({ err: String(e).slice(0, 80) })) : {}),
    log: await page.evaluate(() => window.__labCueLog || []).catch(() => null),
  };
  if (cfg.overflowStrip) out.overflowStripEnd = await stripRows(cfg.overflowStrip);
  out.liveAtEnd = live.size;
  await result({});
} catch (e) {
  await die(String(e).slice(0, 600));
}
