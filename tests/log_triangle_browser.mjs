// The browser driver for tests/test_log_triangle_served.py: the phone bar's Log triangle (#merr) against a hermetic lab
// kernel. Opens the served dashboard with the iPhone 14 descriptor at 390 by 844 (under _MOBILE_MQ, so #mtabs shows), clears
// the Log, and reads the triangle's computed colour, and every other bar button's, at each step of one walk:
//   idle            the Log empty
//   unread          one entry logged (window.__rompNotify, the Log's one write path), on the tab the shell opened on
//   unreadOtherTab  the same, after a tap on another pane tab
//   openSeen        the Log opened by a tap on the triangle, which marks every shown entry seen
//   closedSeen      the Log closed again
//   downUnread      a pane's socket reported down ({romp:'wsState'}, the shims' message), then its redial reported failed
//                   ({romp:'wsFail'}, the shim's word for a dial that closed without opening): a new entry and a live problem
//   downOpen        the Log opened again: everything seen, the socket still down
//   upOpen          the socket reported up, the Log still open
//   openNew         one entry logged with the Log still open: it lands seen, with the mark an opening gives what it shows
//   closedNew       the Log closed: nothing unread was left behind
//   reopenSeen      the Log opened again by a tap on the triangle: the entry is listed, and nothing is unread
//   mutedOpen       a kind muted by a tap on its toggle in the open Log, then one entry of that kind logged: stored unread,
//                   neither listed nor counted while the kind is muted
//   unmutedOpen     the kind unmuted by a second tap, the Log still open: the entry is listed, and seen as it is listed
//   unmutedClosed   the Log closed: nothing unread was left behind
//   lightIdle       the light theme picked (romp:settings, the shell's theme reader), the Log closed, nothing unread
//   lightUnread     one entry logged under the light theme, on another pane tab
// Each snapshot also lists the stylesheet rules that match #merr and declare a colour, in document order (a failure's
// evidence: which rule set the colour), whether the Log's list holds the entry openNew logs (newListed) and the one the muted
// steps log (mutedListed; the list is re-rendered only while the Log is open, so both are read at the open steps), and that
// muted entry's stored seen flag (mutedSeen, null before it is logged). Prints one `RESULT:` JSON line; exits 3
// when the browser does not launch (the Python side turns that into a skip). Never touches a live kernel: cfg.healthz names
// the LAB port and is asserted before any request. No sessions, no real data.
import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";

const require = createRequire(process.env.EXT_PKG);
const playwright = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
const engine = cfg.engine || "chromium";
const now = () => Date.now();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = { engine, errors: [], steps: {} };
const OPEN_TEXT = "Synthetic warning for the triangle test, Log open";   // the entry openNew logs with the Log open
const MUTED_KIND = "retry", MUTED_TEXT = "Synthetic retry for the triangle test, kind muted";   // the entry mutedOpen logs

const healthz = await new Promise((resolve) => {
  const req = http.get(cfg.healthz, (res) => { res.resume(); resolve({ status: res.statusCode }); });
  req.on("error", (e) => resolve({ status: 0, error: String(e) }));
  req.setTimeout(5000, () => { req.destroy(); resolve({ status: 0, error: "timeout" }); });
});
if (healthz.status !== 200) { console.error("lab kernel not healthy: " + JSON.stringify(healthz)); process.exit(4); }

let browser;
try { browser = await playwright[engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }

const result = async (extra) => {
  Object.assign(out, extra || {});
  fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
  try { await browser.close(); } catch (e) { /* closing */ }
  process.exit(0);
};

const dev = { ...(playwright.devices["iPhone 14"] || {}) };
delete dev.defaultBrowserType;
const ctxOpts = { ...dev, viewport: { width: 390, height: 844 } };
if (engine === "firefox") delete ctxOpts.isMobile;   // playwright: isMobile is not supported in Firefox
const context = await browser.newContext(ctxOpts);
const page = await context.newPage();
page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });
// the panes' socket words as the shell hears them, recorded on the top document from its first script: the down step waits
// for the chat pane's own 'up' first, so no late real word from that pane can overwrite the lab's 'down'
await page.addInitScript(() => {
  if (window !== window.top) return;
  window.__labWs = [];
  window.addEventListener("message", (e) => { const m = e && e.data; if (m && m.romp === "wsState") window.__labWs.push(m.app + ":" + m.state); });
});

const frames = () => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
// wait for a page-side condition by polling from here (a predicate evaluated per try, never an async predicate in the page)
const until = async (what, fn, arg, ms = 8000) => {
  const deadline = now() + ms;
  while (now() < deadline) {
    if (await page.evaluate(fn, arg)) return;
    await sleep(50);
  }
  throw new Error("timed out waiting for " + what);
};

const snap = async (name) => {
  await frames();
  out.steps[name] = await page.evaluate(([openText, mutedText]) => {
    const m = document.getElementById("merr");
    if (!m) return { missing: true };
    const cs = getComputedStyle(m);
    const path = m.querySelector("path");
    const txt = m.querySelector(".rerr-n");
    const bar = document.getElementById("mtabs");
    const others = Array.from(document.querySelectorAll("#mtabs button")).filter((b) => b !== m && !b.hidden).map((b) => ({
      key: b.getAttribute("data-pane") ? "pane:" + b.getAttribute("data-pane") : (b.getAttribute("data-act") || b.id),
      on: b.classList.contains("on"), color: getComputedStyle(b).color }));
    const rules = [];
    const walk = (list, media) => {
      for (const r of Array.from(list || [])) {
        if (r.cssRules && r.media) {   // a media block: read inside it only while it applies here
          if (window.matchMedia(r.media.mediaText).matches) walk(r.cssRules, r.media.mediaText);
          continue;
        }
        if (r.selectorText && r.style && r.style.color) {
          let hit = false;
          try { hit = m.matches(r.selectorText); } catch (e) { /* a selector this engine cannot parse */ }
          if (hit) rules.push({ selector: r.selectorText, color: r.style.color, media });
        }
      }
    };
    for (const sh of Array.from(document.styleSheets)) { try { walk(sh.cssRules, ""); } catch (e) { /* cross-origin */ } }
    const listedText = (t) => Array.from(document.querySelectorAll("#rerr-list .rerr-msg")).some((x) => x.textContent.indexOf(t) === 0);
    let mutedSeen = null;
    try {
      const n = (JSON.parse(localStorage.getItem("romp:notices") || "[]") || []).find((x) => x && x.text === mutedText);
      mutedSeen = n ? !!n.seen : null;
    } catch (e) { mutedSeen = "unreadable: " + e; }
    return { has: m.classList.contains("has"), color: cs.color, stroke: path ? getComputedStyle(path).stroke : null,
             textFill: txt ? getComputedStyle(txt).fill : null, digit: txt ? txt.textContent : null,
             logOpen: !document.getElementById("rerr-back").hidden, tab: document.body.getAttribute("data-tab"),
             light: document.body.classList.contains("theme-light"), barDisplay: bar ? getComputedStyle(bar).display : null,
             newListed: listedText(openText), mutedListed: listedText(mutedText), mutedSeen,
             others, rules };
  }, [OPEN_TEXT, MUTED_TEXT]);
  return out.steps[name];
};

const otherTab = () => page.evaluate(() => {   // a shown pane tab other than the current one
  const cur = document.body.getAttribute("data-tab");
  const b = Array.from(document.querySelectorAll("#mtabs button[data-pane]"))
    .find((x) => !x.hidden && x.getAttribute("data-pane") !== cur && getComputedStyle(x).display !== "none");
  return b ? b.getAttribute("data-pane") : null;
});
const tapTab = async (k) => {
  await page.click("#mtabs button[data-pane=" + k + "]");
  await until("the " + k + " tab", (p) => document.body.getAttribute("data-tab") === p, k);
};
const has = (want) => until("#merr.has " + want, (w) => document.getElementById("merr").classList.contains("has") === w, want);

try {
  out.t0 = now();
  await page.goto(cfg.url, { waitUntil: "load", timeout: 40000 });
  await until("the phone shell", () => {
    const m = document.getElementById("merr"), bar = document.getElementById("mtabs");
    const boot = document.getElementById("romp-boot");
    return !!(m && bar && getComputedStyle(bar).display === "flex" && typeof window.__rompNotify === "function"
              && typeof window.__rompOpenErrs === "function" && document.body.getAttribute("data-tab")
              && (!boot || boot.classList.contains("gone")));
  }, null, cfg.bootTimeoutMs || 30000);
  out.bootMs = now() - out.t0;
  await sleep(cfg.settleMs || 500);
  // a known start: the Log emptied through its own Clear all (the button's handler runs with the panel closed)
  await page.evaluate(() => document.getElementById("rerr-clear").click());
  await has(false);
  await snap("idle");
  await page.evaluate(() => window.__rompNotify("warn", "Synthetic warning for the triangle test"));
  await has(true);
  await snap("unread");
  const k1 = await otherTab();
  if (!k1) throw new Error("no other pane tab to tap");
  await tapTab(k1);
  await snap("unreadOtherTab");
  await page.click("#merr");   // the triangle itself opens the Log, and opening marks every shown entry seen
  await until("the Log open", () => !document.getElementById("rerr-back").hidden);
  await has(false);
  await snap("openSeen");
  await page.evaluate(() => window.__rompCloseErrs());
  await until("the Log closed", () => document.getElementById("rerr-back").hidden);
  await snap("closedSeen");
  // a live problem: the chat pane's socket reported down, as its shim reports it (logs one entry and holds the cue while down)
  await until("the chat pane's socket up", () => (window.__labWs || []).indexOf("chat:up") >= 0, null, 20000);
  await page.evaluate(() => window.postMessage({ romp: "wsState", app: "chat", state: "down" }, "*"));
  // then the shim's word that the pane's redial closed without opening, so the step reads one unread entry from either Log: one
  // that writes the connection-lost entry when a reconnect fails writes it on this word, and one that writes it at the drop has
  // written it already and has no listener for the word
  await page.evaluate(() => window.postMessage({ romp: "wsFail", app: "chat" }, "*"));
  await has(true);
  await snap("downUnread");
  await page.click("#merr");
  await until("the Log open", () => !document.getElementById("rerr-back").hidden);
  await snap("downOpen");
  await page.evaluate(() => window.postMessage({ romp: "wsState", app: "chat", state: "up" }, "*"));
  await has(false);
  await snap("upOpen");
  // an entry that arrives while the Log is open lands seen, with the mark an opening gives what it shows
  await page.evaluate((t) => window.__rompNotify("warn", t), OPEN_TEXT);
  // waits on the entry being listed (the write path's own paint renders the open list), not on has, which this step expects
  // to stay as it was: a tree that leaves the arrival unread is red at this step's assertion, not at a timeout
  const listed = (t) => Array.from(document.querySelectorAll("#rerr-list .rerr-msg")).some((x) => x.textContent.indexOf(t) === 0);
  await until("the entry listed in the open Log", listed, OPEN_TEXT);
  await snap("openNew");
  await page.evaluate(() => window.__rompCloseErrs());
  await until("the Log closed", () => document.getElementById("rerr-back").hidden);
  await snap("closedNew");
  await page.click("#merr");
  await until("the Log open", () => !document.getElementById("rerr-back").hidden);
  await until("the entry listed in the reopened Log", listed, OPEN_TEXT);
  await snap("reopenSeen");
  // an unmute with the Log open (2026-10-04): an entry an open Log shows is seen, so the entry the unmute lists leaves the
  // triangle grey there and after the close. The toggles sit in the Log's panel, so the walk can drive no unmute with the Log
  // closed, as a person cannot; tests/test_error_center.py reads that branch against the Log script
  const chip = "#rerr-fgrid .rerr-fbtn.k-" + MUTED_KIND;
  await page.click(chip);
  await until("the kind muted", (sel) => document.querySelector(sel).classList.contains("off"), chip);
  await page.evaluate(([k, t]) => window.__rompNotify(k, t), [MUTED_KIND, MUTED_TEXT]);
  await until("the muted kind's entry stored", (t) => (JSON.parse(localStorage.getItem("romp:notices") || "[]") || [])
    .some((x) => x && x.text === t), MUTED_TEXT);
  await snap("mutedOpen");
  await page.click(chip);
  // waits on the entry being listed (the toggle's own render), not on has, which this step expects to stay as it was: a tree
  // that lists the entry unread is red at this step's assertion, not at a timeout
  await until("the unmuted kind's entry listed in the open Log", listed, MUTED_TEXT);
  await snap("unmutedOpen");
  await page.evaluate(() => window.__rompCloseErrs());
  await until("the Log closed", () => document.getElementById("rerr-back").hidden);
  await snap("unmutedClosed");
  // the light theme, picked the way the gear picks it: the settings object, then the event the shell's theme reader hears
  await page.evaluate(() => {
    let s = {};
    try { s = JSON.parse(localStorage.getItem("romp:settings") || "{}") || {}; } catch (e) { s = {}; }
    s.theme = "yatharth-light";
    localStorage.setItem("romp:settings", JSON.stringify(s));
    window.dispatchEvent(new Event("romp:settings"));
  });
  await until("the light theme", () => document.body.classList.contains("theme-light"));
  await snap("lightIdle");
  const k2 = await otherTab();
  if (k2) await tapTab(k2);
  await page.evaluate(() => window.__rompNotify("warn", "Synthetic warning for the triangle test, light"));
  await has(true);
  await snap("lightUnread");
  await result({});
} catch (e) {
  await result({ died: String(e).slice(0, 600) });
}
