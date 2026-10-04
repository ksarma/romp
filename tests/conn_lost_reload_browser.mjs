// The real-socket driver for tests/test_conn_lost_log_served.py's unload legs (review round 1 of iOS item 4b, 2026-10-04):
// what the Log writes when the page's OWN unload closes a dial that never opened, and that a navigation which fires
// beforeunload but does not unload leaves a later outage logged.
//
// Why real sockets: tests/conn_lost_log_browser.mjs routes every /ws through page.routeWebSocket, a mock no engine closes on
// unload. Firefox closes the old page's never-opened dials after beforeunload and before pagehide and delivers their close
// events while the page still runs (the review measured 1 to 2 ms after beforeunload, about 10 ms before pagehide), and only
// a real socket shows it. So this driver serves the dashboard through a TCP proxy of its own on cfg.proxyPort (a port the
// Python side reserved through tests/lab_ports.py), in front of the lab kernel on cfg.kernelPort. The proxy forwards every
// request; a plain HTTP request has its Connection header set to close, so each request arrives on a connection of its own
// and the proxy reads every path. Every new /ws dial meets the proxy's mode at its arrival:
//   pass     forwarded to the kernel and held as a live socket pair
//   hold     never forwarded and never answered: the page's socket stays CONNECTING until the page closes it (only the
//            apps in cfg.holdApps when it is set; any other app's dial passes)
//   refuse   the connection is destroyed at once: the dial closes without ever opening (the kernel is down)
// A held dial stays held when the mode changes, so a dial in flight at a reload is still CONNECTING when the page unloads.
// drop() destroys every live socket pair: the OS dropping the sockets while the page slept. /__lab/nocontent answers 204.
//
// cfg.scenario:
//   reload-return  boot, read the Log, suspend (every document hidden, mode hold, every socket dropped), return 400 ms later:
//                  the shell's return dial is held (its panes wait on its link and dial nothing), then reload while it is
//                  CONNECTING. The road: the shell's close calls window.__rompLinkFailed for a dial that never opened.
//   reload-boot    mode hold from the first byte for the shown panes (cfg.holdApps), so their boot dials are CONNECTING,
//                  then reload. The road: each pane's close posts its down word and its wsFail word to the shell. Only the
//                  shown panes are held: WebKit counts a socket's handshake against its six connections to a host, so
//                  holding all seven dials starved the page's own loads until the 15 s cuts.
//   nav204-outage  boot, read the Log, navigate the top document to a 204 (beforeunload fires, the page stays; Firefox also
//                  closes every socket of the page, which redial), wait for every socket to be up again, then a real
//                  outage (mode refuse, every socket dropped): the Log owes its entries.
// The page's recorders write to localStorage (lab:ev, lab:notify, lab:sock), so what the OLD page did during its unload
// survives the reload; every row carries its document's generation id (gen). Prints one `RESULT:` JSON line; exits 3 when
// the browser does not launch (the Python side turns that into a skip). Never touches a live kernel: cfg.healthz names the
// LAB port and is asserted before any request. Synthetic sessions only.
import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";
import net from "node:net";

const require = createRequire(process.env.EXT_PKG);
const playwright = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
const engine = cfg.engine || "chromium";
const EAGER = cfg.eagerApps || [];
if (!EAGER.length) { console.error("empty eager set in cfg"); process.exit(5); }
const now = () => Date.now();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = { engine, shell: cfg.shell, scenario: cfg.scenario, t: {}, dials: [], errors: [] };

const healthz = await new Promise((resolve) => {
  const req = http.get(cfg.healthz, (res) => { res.resume(); resolve({ status: res.statusCode }); });
  req.on("error", (e) => resolve({ status: 0, error: String(e) }));
  req.setTimeout(5000, () => { req.destroy(); resolve({ status: 0, error: "timeout" }); });
});
if (healthz.status !== 200) { console.error("lab kernel not healthy: " + JSON.stringify(healthz)); process.exit(4); }

// --- the proxy ---
const PX = { mode: "pass", live: new Set(), held: new Set(), conns: new Set() };
const appOf = (path) => { const m = /[?&]app=([^&]*)/.exec(path); return m ? decodeURIComponent(m[1]) : "?"; };
const proxy = net.createServer((c) => {
  PX.conns.add(c);
  c.on("close", () => PX.conns.delete(c));
  c.on("error", () => { /* the page went away */ });
  let head = Buffer.alloc(0);
  const onData = (b) => {
    head = Buffer.concat([head, b]);
    const end = head.indexOf("\r\n\r\n");
    if (end < 0) return;
    c.removeListener("data", onData);
    c.pause();
    const text = head.subarray(0, end).toString("latin1");
    const rest = head.subarray(end + 4);
    const path = (text.split("\r\n")[0].split(" ")[1]) || "";
    if (path.startsWith("/__lab/nocontent")) { c.end("HTTP/1.1 204 No Content\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"); return; }
    const ws = /^\/ws(\?|$)/.test(path);
    let first = head;
    if (ws) {
      const d = { app: appOf(path), t: now(), mode: PX.mode };
      out.dials.push(d);
      if (PX.mode === "refuse") { d.verdict = "refused"; c.destroy(); return; }
      if (PX.mode === "hold" && (!cfg.holdApps || cfg.holdApps.includes(d.app))) {
        d.verdict = "held";
        PX.held.add(c);
        c.on("close", () => { PX.held.delete(c); d.closedT = now(); });
        c.resume();   // read and discard: the page's close is what ends it
        return;
      }
      d.verdict = "passed";
    } else {
      first = Buffer.concat([Buffer.from(text.split("\r\n").filter((l) => !/^connection:/i.test(l)).join("\r\n") + "\r\nConnection: close\r\n\r\n", "latin1"), rest]);
    }
    const u = net.connect(cfg.kernelPort, "127.0.0.1", () => { u.write(first); c.pipe(u); u.pipe(c); c.resume(); });
    const pair = { c, u };
    if (ws) PX.live.add(pair);
    const done = () => { PX.live.delete(pair); c.destroy(); u.destroy(); };
    u.on("error", done); u.on("close", done); c.on("close", done);
  };
  c.on("data", onData);
});
await new Promise((resolve, reject) => { proxy.once("error", reject); proxy.listen(cfg.proxyPort, "127.0.0.1", resolve); });
const drop = () => { const n = PX.live.size; for (const p of Array.from(PX.live)) { PX.live.delete(p); p.c.destroy(); p.u.destroy(); } return n; };
const base = "http://127.0.0.1:" + cfg.proxyPort;

let browser;
try { browser = await playwright[engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); proxy.close(); process.exit(3); }
const result = async (extra) => {
  Object.assign(out, extra || {});
  fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
  try { await browser.close(); } catch (e) { /* closing */ }
  for (const c of Array.from(PX.conns)) c.destroy();
  proxy.close();
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

// --- every document: the visibility override and a socket recorder; the top document: the Log's recorders ---
await page.addInitScript(() => {
  const w = window;
  if (document.__labInit) return;
  document.__labInit = true;
  if (w.__labHidden === undefined) w.__labHidden = false;
  try {
    Object.defineProperty(document, "visibilityState", { get: () => (w.__labHidden ? "hidden" : "visible"), configurable: true });
    Object.defineProperty(document, "hidden", { get: () => !!w.__labHidden, configurable: true });
  } catch (e) { /* the boot read shows a frame without it */ }
  const top = w === w.top;
  const gen = top ? (w.__labGen = w.__labGen || Math.random().toString(36).slice(2, 10)) : ((w.top && w.top.__labGen) || "?");
  const rec = (k, v) => { try { const a = JSON.parse(localStorage.getItem(k) || "[]"); a.push(Object.assign({ gen, t: Date.now() }, v)); localStorage.setItem(k, JSON.stringify(a)); } catch (e) { /* recording only */ } };
  try {
    const RW = w.WebSocket;
    const LabWS = function (u, p) {
      const s = p === undefined ? new RW(u) : new RW(u, p);
      const app = (/[?&]app=([^&]*)/.exec(String(u)) || [])[1] || "?", t0 = Date.now();
      rec("lab:sock", { ev: "dial", app, top });
      s.addEventListener("open", () => rec("lab:sock", { ev: "open", app, top, age: Date.now() - t0 }));
      s.addEventListener("close", (e) => rec("lab:sock", { ev: "close", app, top, code: e.code, age: Date.now() - t0 }));
      return s;
    };
    LabWS.prototype = RW.prototype; LabWS.CONNECTING = 0; LabWS.OPEN = 1; LabWS.CLOSING = 2; LabWS.CLOSED = 3;
    w.WebSocket = LabWS;
  } catch (e) { /* recording only */ }
  if (!top) return;
  for (const k of ["beforeunload", "pagehide", "pageshow"]) w.addEventListener(k, () => rec("lab:ev", { ev: k }));
  w.addEventListener("message", (e) => {
    const m = e && e.data;
    if (m && (m.romp === "wsState" || m.romp === "wsFail")) rec("lab:ev", { ev: m.romp, app: m.app, state: m.state || "", cut: m.cut });
  });
  const wrap = (name, before) => {
    let real;
    Object.defineProperty(w, name, { configurable: true, get: () => real, set: (f) => {
      real = typeof f !== "function" ? f : function () { before.apply(this, arguments); return f.apply(this, arguments); };
    } });
  };
  wrap("__rompNotify", (kind, text) => rec("lab:notify", { kind: String(kind), text: String(text) }));
  wrap("__rompLinkFailed", (cut) => rec("lab:ev", { ev: "linkFailed", cut }));
});
const flip = (hidden) => page.evaluate((h) => {
  const done = [];
  for (const f of [window].concat(Array.from(window.frames))) {
    try { f.__labHidden = h; f.document.dispatchEvent(new f.Event("visibilitychange")); done.push(f.location.pathname); }
    catch (e) { done.push("ERR:" + String(e).slice(0, 80)); }
  }
  return done;
}, hidden);
const store = () => page.evaluate(() => {
  const j = (k) => { try { return JSON.parse(localStorage.getItem(k) || "[]"); } catch (e) { return ["UNREADABLE"]; } };
  return { ev: j("lab:ev"), notify: j("lab:notify"), sock: j("lab:sock"),
           notes: j("romp:notices").map((x) => ({ kind: x.kind, text: x.text, seen: !!x.seen, n: x.n || 1 })),
           gen: window.__labGen, bodyClass: document.body.className };
});
const readLog = () => page.evaluate(() => {
  let notes = [];
  try { notes = JSON.parse(localStorage.getItem("romp:notices") || "[]"); } catch (e) { notes = ["UNREADABLE"]; }
  const el = document.getElementById("merr"), n = el && el.querySelector(".rerr-n");
  return { t: Date.now(), entries: notes.map((x) => ({ kind: x.kind, text: x.text, seen: !!x.seen, n: x.n || 1 })),
           digit: n ? n.textContent : null, has: !!(el && el.classList.contains("has")) };
});
// every eager pane said up and the link reads up, counting only words of this document generation since sinceT
const waitUp = async (sinceT, ms) => {
  const deadline = now() + ms;
  while (now() < deadline) {
    try {
      const r = await page.evaluate((t) => {
        const s = {}; let a = [];
        try { a = JSON.parse(localStorage.getItem("lab:ev") || "[]"); } catch (e) { a = []; }
        for (const x of a) if (x.ev === "wsState" && x.gen === window.__labGen && x.t >= t) s[x.app] = x.state;
        return { s, link: !!(window.__rompLink && window.__rompLink().up) };
      }, sinceT);
      if (r.link && EAGER.every((a) => r.s[a] === "up")) return true;
    } catch (e) { /* a navigation in progress */ }
    await sleep(100);
  }
  return false;
};
// the page's latest socket for app, of this generation: CONNECTING when it has a dial and no open or close yet
const connecting = (app) => page.evaluate((a) => {
  let s = [];
  try { s = JSON.parse(localStorage.getItem("lab:sock") || "[]"); } catch (e) { s = []; }
  s = s.filter((x) => x.gen === window.__labGen && x.app === a);
  let state = "none";
  for (const x of s) state = x.ev === "dial" ? "connecting" : x.ev === "open" ? "open" : "closed";
  return state === "connecting";
}, app);
const waitFor = async (pred, ms) => { const dl = now() + ms; while (now() < dl) { try { if (await pred()) return true; } catch (e) { /* retry */ } await sleep(50); } return false; };
const readOnce = async () => { await page.evaluate(() => { window.__rompOpenErrs(); window.__rompCloseErrs(); }); };
const clearRecords = () => page.evaluate(() => { for (const k of ["lab:ev", "lab:notify", "lab:sock"]) localStorage.setItem(k, "[]"); });

try {
  const url = base + "/?token=" + encodeURIComponent(cfg.token);
  if (cfg.scenario === "reload-boot") {
    PX.mode = "hold";
    out.t.load = now();
    await page.goto(url, { waitUntil: "load", timeout: 40000 });
    out.oldGen = await page.evaluate(() => window.__labGen);
    // every held pane's boot dial is CONNECTING (Firefox and Chromium hold a host's handshakes in one line, so a dial
    // behind a held one never reaches the proxy; the page reads it CONNECTING all the same)
    out.allConnecting = await waitFor(async () => {
      for (const a of cfg.holdApps || EAGER) if (!(await connecting(a))) return false;
      return true;
    }, 30000);
    if (!out.allConnecting) await result({ died: "boot: not every held dial was CONNECTING", rec: await store() });
    await sleep(cfg.connectingMs || 500);
    out.bodyClass = await page.evaluate(() => document.body.className);
    PX.mode = "pass";
    out.t.reload = now();
    await page.reload({ waitUntil: "load", timeout: 40000 });
  } else {
    out.t.load = now();
    await page.goto(url, { waitUntil: "load", timeout: 40000 });
    out.bootUp = await waitUp(0, cfg.bootTimeoutMs || 30000);
    if (!out.bootUp) await result({ died: "boot: not every eager pane and the link said up", rec: await store() });
    out.bodyClass = await page.evaluate(() => document.body.className);
    await sleep(cfg.settleMs || 1500);
    await readOnce();   // the person read the Log: whatever the boot logged is seen from here
    out.logAtBoot = await readLog();
    out.oldGen = await page.evaluate(() => window.__labGen);
    if (cfg.scenario === "reload-return") {
      await clearRecords();   // from here the records are the return's and the reload's
      PX.mode = "hold";
      out.t.suspend = now();
      await flip(true);
      out.dropped = drop();
      await sleep(cfg.hiddenDwellMs || 400);
      out.t.return = now();
      await flip(false);
      out.shellConnecting = await waitFor(() => connecting("shell"), 15000);
      if (!out.shellConnecting) await result({ died: "return: the shell's dial was never CONNECTING", rec: await store() });
      await sleep(cfg.connectingMs || 300);
      PX.mode = "pass";
      out.t.reload = now();
      await page.reload({ waitUntil: "load", timeout: 40000 });
    } else if (cfg.scenario === "nav204-outage") {
      out.t.nav = now();
      await page.evaluate(() => { setTimeout(() => { location.href = "/__lab/nocontent"; }, 0); });
      await sleep(cfg.navSettleMs || 1500);
      out.genAfterNav = await page.evaluate(() => window.__labGen);
      out.navUp = await waitUp(0, cfg.upTimeoutMs || 25000);   // each socket's latest word: Firefox's redials, or Chromium's sockets that never closed
      if (!out.navUp) await result({ died: "after the 204: not every eager pane and the link said up again", rec: await store() });
      await sleep(cfg.settleMs || 1500);
      PX.mode = "refuse";
      out.t.outage = now();
      out.dropped = drop();
      out.reads = [];
      for (const at of cfg.readsMs || []) { await sleep(Math.max(0, out.t.outage + at - now())); out.reads.push({ at, log: await readLog() }); }
      await sleep(Math.max(0, out.t.outage + (cfg.outageMs || 5000) - now()));
      PX.mode = "pass";
      out.t.outageEnd = now();
    } else {
      await result({ died: "unknown scenario " + cfg.scenario });
    }
  }
  out.newGen = await page.evaluate(() => window.__labGen);
  out.upAfter = await waitUp(cfg.scenario === "nav204-outage" ? out.t.outageEnd : 0, cfg.upTimeoutMs || 25000);
  out.t.up = now();
  await sleep(cfg.afterMs || 2000);   // anything the page still had to say lands in this window
  out.logAfter = await readLog();
  out.rec = await store();
  out.t.done = now();
  await result({});
} catch (e) {
  let rec = null;
  try { rec = await store(); } catch (e2) { /* the page is gone */ }
  await result({ died: String(e).slice(0, 600), rec });
}
