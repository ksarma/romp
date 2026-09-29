// The browser driver for tests/test_reply_sheet_served.py: the todo Reply sheet, as the kernel serves it in the Waiting
// pane (/waiting) and the chat page (/chat), on a phone with the keyboard up, against a hermetic lab kernel. The
// composition the maintainer's round 1 ruling on PR 859 asked for: at 390 by 508 (the pane's own innerHeight IS the
// fold's signal: inside the shell the pane iframe is sized to the visible height), a todo with a wrapped ask, a file
// chip, a link chip and a forty-line detail whose first line carries an address and whose last line is an unbreakable
// token; the sheet opened, fourteen lines typed, then a real click at Send's painted centre. Read back: the box's children
// (the tree each builder emits), Send's and Cancel's rects against the box's clip and the frame, what elementFromPoint
// finds at Send's centre, the detail's height against its two-line floor, and what the click did: is the overlay still
// up, and did the page's socket carry a userTodoAnswer frame for the todo (WebSocket.prototype.send is wrapped by an init
// script, so a send is observed as the bytes the page put on its socket, whatever the kernel then does with them).
//
// Before the tap, the states the fix's other rules and handlers are for, each read from the engine where CI has one
// (the two node browser legs measure the same and skip in CI's Test step): the window at 300px (the fold on: the sheet
// pinned to the top under the picker's 12px frame, the detail at its floor and scrolling, its first line's address under
// a finger where the engine's own scroll left it and once the box is scrolled to bring its line to the top of the box's
// view, Send inside the clip and under a finger
// at the box's bottom); at 420px with the same todo (the pane's two chip rows put the floors past the fold's cap, so its box
// scrolls a few pixels, and the actions row, kept in view at the box's bottom, holds Cancel and Send inside the clip; the
// chat's column fits); the detail's scrollWidth against its offsetWidth, the border box,
// with the unbreakable token wrapped (overflow-wrap: anywhere); the answer typed at 900px and the window then shrunk to
// 508 (kbFit re-runs grow on the resize: the answer box re-fits to the room). After the tap, on the other todo: an
// inline height written as the resize grip writes it, then one keystroke (the drag guard: the height stands); the height
// written to 215px and the frame taken to 420 and back (the dragged height is a preference: clamped to the room under the
// fold, not to the content, and returned to at 508); then the grip pulled past the box's bottom edge and released over the backdrop, then a
// text selection dragged from inside the box onto the backdrop and released (a click whose press began inside the sheet is
// not a backdrop tap: the sheet stands with its text after both; Chromium and WebKit dispatch that click to the overlay,
// Firefox to the textarea), and a plain tap on the backdrop, press and release both on it (it dismisses).
//
// After the send the chat page's card is REBUILT by the kernel's pushes that follow it (askLiveClear and chatTail frames;
// the pane's list gets no push after the send here): the other todo's Reply button becomes
// a new node, and a driver that resolved the old one and then acted on it died with "Element is not attached to the DOM"
// (PR 859's CI at the pass's pushed head, chromium chat; the reviewer's forcings: the sheet's own node survives that
// rebuild in both panes, so this is the driver's race, not the sheet's). So the driver tags the other todo's button before
// the tap, waits for it to be replaced after the send where the card is rebuilt (the chat), opens the sheet with one
// fresh click on the button, and records a button that vanished under it or did not open the sheet as its own failure
// line naming the element, never a bare exception.
// The detail's cap at rest (the maintainer's ruling at the merge with main): with the keyboard down it is the larger of
// 12em and 34.8% of the window's height, with the keyboard up 12em, as before. Read at rest at 900 and 1080 and at the
// pane heights a phone gives (the maintainer's rulings on the cap pass and on the share: the installed app's 732, and
// Safari's 709, 633 and 620) on the composition's todo with its answer box cleared (the viewport term), and under the
// keyboard at 508 on the other todo's sheet at open (12em). Then, on a third todo whose detail is the recorded 8-line
// one, the stated boundary (styles.css: in full from a 720px pane): at the app's 732 and at 720, then one pixel under
// this engine's own boundary (cfg.belowBoundary) and at Safari's common 633. Last, in Chromium, on the same sheet, a finger
// through the DevTools protocol's touch input pressed just outside the box's left edge and lifted just inside it, at 900 and
// 508 (the sheet stands with its answer: a backdrop press gives back the implicit capture a touch pointer takes), and a
// finger's tap on the backdrop (it dismisses). The detail's cap reads the keyboard where
// the shell does (restCap; kernel.py kbOpen): the visual viewport of the window that owns the screen shorter than its
// layout viewport. These pages are top-level, so that window is the page itself: with the keyboard up the driver stubs
// its visualViewport.height to its innerHeight less a phone keyboard's 336px, and removes the stub at rest; every window
// under 900 is the keyboard up unless the step says it is at rest.
// Prints one `RESULT:` JSON line; exits 3 when the browser does not launch (the Python side turns that into a skip), 4
// when the LAB kernel is not healthy (cfg.healthz names the lab port, asserted before any request; never a live kernel).
// Synthetic sessions and todos only.
import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";

const require = createRequire(process.env.EXT_PKG);
const playwright = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
const engine = cfg.engine || "chromium";
const out = { engine, pane: cfg.pane, errors: [] };
const W = 390, KEYBOARD_UP = 508, TIGHT = 420, SHORT = 300, TALL = 900, REST_TALL = 1080, KEYBOARD_H = 336;
// the pane heights a phone gives at rest (styles.css, where the share is derived): Safari's panes (a window less the phone
// shell's 31px tab bar: 651, 664 and 740), the installed app's pane on a 390x844 phone (its window, the screen less the
// status bar, less the app's 65px tab bar), and the stated boundary, where the recorded 8-line detail starts to show in full
const SAFARI_16E = 620, SAFARI_BARS = 633, SAFARI_TOP = 709, APP_PANE = 732, BOUNDARY = 720;
const ANSWER = Array.from({ length: 14 }, (_, i) => `line ${i + 1}`).join("\n");

const healthz = await new Promise((resolve) => {
  const req = http.get(cfg.healthz, (res) => { res.resume(); resolve({ status: res.statusCode }); });
  req.on("error", (e) => resolve({ status: 0, error: String(e) }));
  req.setTimeout(5000, () => { req.destroy(); resolve({ status: 0, error: "timeout" }); });
});
if (healthz.status !== 200) { console.error("lab kernel not healthy: " + JSON.stringify(healthz)); process.exit(4); }

let browser;
try { browser = await playwright[engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + String(e).split("\n")[0]); process.exit(3); }

const result = async (extra) => {
  Object.assign(out, extra || {});
  fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
  try { await browser.close(); } catch (e) { /* closing */ }
  process.exit(0);
};

const context = await browser.newContext({ viewport: { width: W, height: KEYBOARD_UP } });
const page = await context.newPage();
page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });
// every frame the page puts on a socket, before any page script: a Send is the userTodoAnswer frame among them
await page.addInitScript(() => {
  window.__wsSent = [];
  const send = WebSocket.prototype.send;
  WebSocket.prototype.send = function (data) { try { window.__wsSent.push(String(data).slice(0, 600)); } catch (e) { /* not text */ } return send.call(this, data); };
});
const settle = () => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
// the keyboard's signal for the detail's cap (restCap): this top-level page's visual viewport stubbed shorter than its
// layout viewport by a keyboard's height, or the stub removed (at rest the engine's getter answers, the viewport's height)
const keyboard = (on) => page.evaluate(([o, kh]) => {
  if (!o) delete window.visualViewport.height;
  else Object.defineProperty(window.visualViewport, "height", { configurable: true, get: () => Math.max(0, window.innerHeight - kh) });
}, [on, KEYBOARD_H]);
// a window under 900 is the keyboard up; the keyboard's state is set before the resize, so kbFit reads it
const setHeight = async (h, kb = h < TALL) => {
  await keyboard(kb);
  await page.setViewportSize({ width: W, height: h });
  await page.waitForFunction((hh) => window.innerHeight === hh, h, { timeout: 10000 });
  await settle();
};
const waitTight = (on) => page.waitForFunction((want) => document.getElementById("ut-reply-prompt")?.classList.contains("kb-tight") === want, on, { timeout: 10000 });
const fill = async (text) => { await page.locator("#ut-reply-prompt .ut-reply-input").fill(text); await settle(); };

// the sheet's geometry, read in the page
const measure = () => page.evaluate(() => {
  const overlay = document.getElementById("ut-reply-prompt");
  if (!overlay) return null;
  const box = overlay.querySelector(".confirm-box");
  const input = overlay.querySelector(".ut-reply-input");
  const detail = overlay.querySelector(".ut-detail");
  const quote = overlay.querySelector(".ut-reply-quote");
  const [cancel, send] = overlay.querySelectorAll(".confirm-actions button");
  const cs = (e) => getComputedStyle(e);
  const rect = (e) => { const r = e.getBoundingClientRect(); return { top: +r.top.toFixed(1), bottom: +r.bottom.toFixed(1), left: +r.left.toFixed(1), right: +r.right.toFixed(1) }; };
  const hit = (e) => { const r = e.getBoundingClientRect(); const at = document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2);
    return at === e ? "target" : at === overlay ? "overlay" : at === box ? "box" : at ? (at.className || at.tagName).split(" ")[0] : "none"; };
  // the three-row height in THIS engine: a probe of the same class, rows=3, laid out OUT OF FLOW (position fixed: the chat
  // page's body is a full-height flex column, and a probe appended in flow there is a shrinkable flex item, the very
  // squeeze under test); measured and removed
  const probe = document.createElement("textarea"); probe.className = "ut-reply-input"; probe.rows = 3;
  probe.style.position = "fixed"; probe.style.top = "0"; probe.style.left = "0"; probe.style.width = "300px"; probe.style.visibility = "hidden";
  document.body.appendChild(probe); const floorH = probe.clientHeight; probe.remove();
  // the detail's sideways overflow: its scrollWidth (the content's width, trailing spaces that hang at a soft wrap left
  // out) against its offsetWidth (the border box; not clientWidth, which a classic vertical scrollbar in WebKit headless
  // narrows by its own width while the text still lays out to the border box). An unbreakable token that does not wrap
  // makes scrollWidth hundreds of pixels wider. The widest text rect is kept beside it for the record only: at a soft
  // wrap the collapsed trailing space hangs a few pixels past the line box and Range.getClientRects reports it
  const textRight = (e) => { const rg = document.createRange(); rg.selectNodeContents(e); return +Array.from(rg.getClientRects()).reduce((w, x) => Math.max(w, x.right), 0).toFixed(1); };
  return {
    frameH: window.innerHeight, tight: overlay.classList.contains("kb-tight"), alignItems: cs(overlay).alignItems, paddingTop: cs(overlay).paddingTop,
    inputH: input.clientHeight, floorH,
    detailH: detail ? detail.clientHeight : null, detailScrollH: detail ? detail.scrollHeight : null, detailOverflowY: detail ? cs(detail).overflowY : null,
    detailOverflowX: detail ? cs(detail).overflowX : null, detailScrollW: detail ? detail.scrollWidth : null, detailOffsetW: detail ? detail.offsetWidth : null,
    detailTextRight: detail ? textRight(detail) : null, detailRight: detail ? +detail.getBoundingClientRect().right.toFixed(1) : null,
    detailLineH: detail ? parseFloat(cs(detail).lineHeight) : null,
    detailFontPx: detail ? parseFloat(cs(detail).fontSize) : null, detailMaxH: detail ? parseFloat(cs(detail).maxHeight) : null,   // the cap the engine resolved
    detailRectH: detail ? detail.getBoundingClientRect().height : null,   // the detail's laid-out height, unrounded: at its cap it equals the cap; under it, the room set it
    box: rect(box), boxScrollH: box.scrollHeight, boxClientH: box.clientHeight, boxOverflowY: cs(box).overflowY,
    send: rect(send), cancel: rect(cancel), hitAtSend: hit(send), hitAtCancel: hit(cancel),
    kinds: Array.from(box.children).map((c) => (["wt-file", "wt-link", "ut-file", "ut-link"].find((k) => c.classList.contains(k)) || (c.className || c.tagName).split(" ")[0])),
    quoteChips: quote ? Array.from(quote.querySelectorAll(".ut-file, .ut-link")).map((c) => (c.classList.contains("ut-file") ? "ut-file" : "ut-link")) : [],
    inputSel: input.matches("#ut-reply-prompt .ut-reply-input"), detailSel: detail ? detail.matches("#ut-reply-prompt .ut-detail.open") : null, boxSel: box.matches("#ut-reply-prompt .picker-box"), actionsSel: overlay.querySelector(".confirm-actions").matches("#ut-reply-prompt .confirm-actions"),
    // the answer box's sizing, for the record: its inline height (grow's last write), computed min-height and line-height,
    // and every child's laid-out height
    inputStyleH: input.style.height, inputMinH: cs(input).minHeight, inputLineH: cs(input).lineHeight, inputScrollH: input.scrollHeight,
    kids: Array.from(box.children).map((c) => [(["wt-file", "wt-link"].find((k) => c.classList.contains(k)) || (c.className || c.tagName).split(" ")[0]), +c.getBoundingClientRect().height.toFixed(1)]),
  };
});
// a short window, where the box itself may have to scroll: the detail against its floor, whether it scrolls, whether the
// address on its first line is under a finger where the engine's own scroll left it (linkHit) and once the box is scrolled to
// bring its line to the top of the box's view (linkHitScrolled), and Send at the box's bottom
const probeShort = () => page.evaluate(() => {
  const overlay = document.getElementById("ut-reply-prompt");
  const box = overlay.querySelector(".confirm-box");
  const detail = overlay.querySelector(".ut-detail");
  const send = overlay.querySelectorAll(".confirm-actions button")[1];
  const hit = (e) => { const r = e.getBoundingClientRect(); const at = document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2);
    return at === e ? "target" : at === overlay ? "overlay" : at === box ? "box" : at ? (at.className || at.tagName).split(" ")[0] : "none"; };
  const inBox = (e) => { const r = e.getBoundingClientRect(), b = box.getBoundingClientRect(); return r.top >= b.top - 0.5 && r.bottom <= b.bottom + 0.5; };
  box.scrollTop = 0; detail.scrollTop = 0;
  detail.scrollIntoView({ block: "nearest" });
  const a = detail.querySelector("a");
  const first = a ? (a.getClientRects()[0] || a.getBoundingClientRect()) : null;
  const atLink = first ? document.elementFromPoint((first.left + first.right) / 2, (first.top + first.bottom) / 2) : null;
  const linkHit = !a ? "no-link" : atLink === a ? "target" : atLink ? (atLink.className || atLink.tagName).split(" ")[0] : "none";
  // the actions row, kept in view at the box's bottom, can cover what the engine scrolled into view there: the person scrolls
  // the box, and with the address's line brought to the top of the box's view it is under a finger
  if (a && first) box.scrollTop += first.top - (box.getBoundingClientRect().top + box.clientTop);
  const again = a ? (a.getClientRects()[0] || a.getBoundingClientRect()) : null;
  const atLink2 = again ? document.elementFromPoint((again.left + again.right) / 2, (again.top + again.bottom) / 2) : null;
  const linkHitScrolled = !a ? "no-link" : atLink2 === a ? "target" : atLink2 ? (atLink2.className || atLink2.tagName).split(" ")[0] : "none";
  detail.scrollTop = 30; const detailScrolls = detail.scrollTop > 0; detail.scrollTop = 0;
  box.scrollTop = box.scrollHeight;
  const o = { frameH: window.innerHeight, tight: overlay.classList.contains("kb-tight"), alignItems: getComputedStyle(overlay).alignItems, paddingTop: getComputedStyle(overlay).paddingTop,
    detailH: detail.clientHeight, detailLineH: parseFloat(getComputedStyle(detail).lineHeight),
    detailScrolls, linkHit, linkHitScrolled, boxScrollH: box.scrollHeight, boxClientH: box.clientHeight, boxScrollTop: box.scrollTop, sendHitAtBottom: hit(send), sendInBoxAtBottom: inBox(send) };
  box.scrollTop = 0;
  return o;
});
// the click that ends a drag of the grip (the author's pass after the maintainer's round 1, composition-2): every click on
// the document recorded in the capture phase (the record names the click's target per engine); the grip pulled past the
// box's bottom edge and released over the backdrop (the box at its cap cannot grow with the answer box, so the pointer
// leaves it); where the headless grip does not move, the inline height is written under the press, as the grip writes it
const dragRelease = async (past = 30) => {
  await page.evaluate(() => { window.__clicks = []; if (!window.__clickRec) { window.__clickRec = true; document.addEventListener("click", (e) => { window.__clicks.push(String(e.target.id || e.target.className || e.target.tagName).split(" ")[0]); }, true); } });
  const before = await measure();
  const r = await page.evaluate(() => { const i = document.querySelector("#ut-reply-prompt .ut-reply-input").getBoundingClientRect(); const b = document.querySelector("#ut-reply-prompt .confirm-box").getBoundingClientRect(); return { right: i.right, bottom: i.bottom, boxTop: b.top, boxBottom: b.bottom }; });
  await page.mouse.move(r.right - 5, r.bottom - 5);
  await page.mouse.down();
  await page.mouse.move(r.right - 5, r.boxBottom + past - 12, { steps: 8 });
  await page.mouse.move(r.right - 5, r.boxBottom + past, { steps: 4 });
  const mid = await measure();
  let road = "native grip";
  if (mid.inputStyleH === before.inputStyleH) {
    road = "scripted (the headless grip did not move): the inline height written under the press, as the grip writes it";
    await page.evaluate((h) => { document.querySelector("#ut-reply-prompt .ut-reply-input").style.height = h + "px"; }, before.inputH + 60);
    await settle();
  }
  await page.mouse.up();
  await settle();
  await page.waitForTimeout(300);
  const after = await page.evaluate(() => { const i = document.querySelector("#ut-reply-prompt .ut-reply-input"); return { overlayUp: !!document.getElementById("ut-reply-prompt"), value: i ? i.value : null, clicks: window.__clicks }; });
  return { road, endY: r.boxBottom + past, boxTop: r.boxTop, boxBottom: r.boxBottom, inputStyleHMid: mid.inputStyleH, ...after };
};
// the Reply button of a todo, tapped as a person taps it; the chat's card is a collapsible notice whose head is tapped first
const openReply = async (tid) => {
  const replySel = `.ut-reply[data-tid="${tid}"]`;
  if (cfg.pane === "chat") {
    // the card is a collapsible notice whose body is display:none until its head is tapped (styles.css
    // .notice-collapsible:not(.notice-open) > .notice-body): open it the way a person does, through the head
    await page.waitForSelector(replySel, { state: "attached", timeout: 30000 });
    await page.evaluate((sel) => {
      const card = document.querySelector(sel).closest(".notice-collapsible");
      if (card && !card.classList.contains("notice-open")) card.querySelector(".notice-head").click();
    }, replySel);
  }
  try {
    await page.waitForSelector(replySel, { timeout: 30000 });
  } catch (e) {
    // the button is attached and hidden: say which ancestor hides it, so the record names the fold
    out.hiddenBy = await page.evaluate((sel) => {
      const b = document.querySelector(sel); if (!b) return "no button";
      const chain = []; for (let e = b; e && e !== document.body; e = e.parentElement) { const cs = getComputedStyle(e); const r = e.getBoundingClientRect();
        if (cs.display === "none" || cs.visibility === "hidden" || r.height === 0) chain.push([(e.className || e.tagName).split(" ").slice(0, 3).join("."), cs.display, cs.visibility, +r.height.toFixed(1)]); }
      return chain;
    }, replySel);
    throw e;
  }
  // one fresh resolution at the click itself (a locator resolves when it acts, and the click scrolls the button into view):
  // a separate scroll-into-view on a handle resolved earlier is what a rebuild of the card under it detached (PR 859's CI)
  try {
    await page.locator(replySel).first().click({ timeout: 10000 });
    await page.waitForSelector("#ut-reply-prompt .ut-reply-input", { timeout: 10000 });
  } catch (e) {
    const now = await page.evaluate((sel) => ({ button: !!document.querySelector(sel), sheet: !!document.getElementById("ut-reply-prompt") }), replySel);
    throw new Error(`the Reply button for ${tid} (${replySel}) ${now.sheet ? "opened no sheet the driver could read" : now.button ? "is in the page but the click did not open the sheet" : "vanished under the driver: the card was rebuilt between the button's resolution and the click"} (${String(e).split("\n")[0].slice(0, 160)})`);
  }
  await settle();
};
// a text selection dragged out of the box (the reviewer's ruling on the pass's observation): the press inside the textarea's
// text, dragged past the box's bottom edge and released over the backdrop; the same common-ancestor click as the grip's with
// the box's height unchanged. The clicks are recorded as for the pull
const selectRelease = async (past = 20) => {
  await page.evaluate(() => { window.__clicks = []; });
  const r = await page.evaluate(() => { const i = document.querySelector("#ut-reply-prompt .ut-reply-input").getBoundingClientRect(); const b = document.querySelector("#ut-reply-prompt .confirm-box").getBoundingClientRect(); return { left: i.left, top: Math.max(i.top, b.top), boxBottom: b.bottom }; });
  await page.mouse.move(r.left + 20, r.top + 12);
  await page.mouse.down();
  await page.mouse.move(r.left + 60, r.boxBottom + past, { steps: 10 });
  await page.mouse.up();
  await settle();
  await page.waitForTimeout(300);
  const after = await page.evaluate(() => { const i = document.querySelector("#ut-reply-prompt .ut-reply-input"); return { overlayUp: !!document.getElementById("ut-reply-prompt"), value: i ? i.value : null, clicks: window.__clicks }; });
  return { endY: r.boxBottom + past, ...after };
};
// the card's rebuild the send causes: the other todo's Reply button, tagged before the tap, is a NEW node once the kernel's
// pushes have been rendered (the chat). Waited for where the card is rebuilt, so the sheet is opened
// on a card that is not about to be replaced under the click; the wait's outcome is recorded, never asserted (the kernel's
// response to a send is its business), and its absence within the bound is recorded as such
const tagButton = (tid) => page.evaluate((sel) => { window.__tagged = document.querySelector(sel); return !!window.__tagged; }, `.ut-reply[data-tid="${tid}"]`);
const waitForRebuild = async (tid) => {
  const t0 = Date.now();
  try {
    await page.waitForFunction((sel) => { const b = document.querySelector(sel); return !!b && b !== window.__tagged; }, `.ut-reply[data-tid="${tid}"]`, { timeout: 10000 });
    return { replaced: true, ms: Date.now() - t0 };
  } catch (e) { return { replaced: false, ms: Date.now() - t0, note: "no rebuild of the card replaced the other todo's Reply button within 10 s of the send" }; }
};

try {
  await page.goto(cfg.url, { timeout: cfg.bootTimeoutMs || 30000 });
  if (cfg.pane === "chat") {
    // the chat page shows one session's card: bring the todo's session forward through its tab (the desktop strip: a
    // fine pointer at 390px is not the phone layout)
    await page.waitForSelector(`#tabs .tab[data-id="${cfg.sid}"]`, { timeout: 30000 });
    await page.click(`#tabs .tab[data-id="${cfg.sid}"]`);   // every session's thread is in the document; the active one is shown
    await page.waitForFunction((sid) => { const t = document.querySelector(`.thread[data-session="${sid}"]`); return !!t && getComputedStyle(t).display !== "none"; }, cfg.sid, { timeout: 30000 });
  }
  await keyboard(true);   // the page opens at 508, the keyboard up
  await openReply(cfg.tid);
  out.opened = await measure();
  // the short window: the fold on, the floors alone past the cap
  await setHeight(SHORT);
  await waitTight(true);
  out.short = await probeShort();
  // 420px with the same todo: the pane's two chip rows put the floors past the fold's cap (the box scrolls a few pixels, the
  // actions row kept in view at its bottom), the chat's column fits; at open and with fourteen lines typed
  await setHeight(TIGHT);
  await waitTight(true);
  out.at420 = await measure();
  out.at420Bottom = await probeShort();
  await fill(ANSWER);
  out.typed420 = await measure();
  out.typed420Bottom = await probeShort();
  // the answer grown TALL, then the window shrunk to 508 under it: kbFit re-runs grow on the resize, so the box re-fits to
  // the room (the cap's stated purpose)
  await setHeight(TALL);
  await waitTight(false);
  // the keyboard down: the detail's cap at rest with the answer box empty (the answer typed at 420 is cleared, so the room
  // holds more than the cap), the viewport term at 900 and at 1080, then at the installed app's 732, where the share holds
  // this todo's room, and at Safari's 709, 633 and 620, where the pane's room is under the cap and the shrink sets its
  // detail; the answer is typed again at 900 below
  await fill("");
  out.restTall = await measure();
  await setHeight(REST_TALL);
  out.restTaller = await measure();
  await setHeight(APP_PANE, false);
  out.restApp = await measure();
  await setHeight(SAFARI_TOP, false);
  out.restSafariTop = await measure();
  await setHeight(SAFARI_BARS, false);
  out.restSafari = await measure();
  await setHeight(SAFARI_16E, false);
  out.restSafari16e = await measure();
  await setHeight(TALL);
  await fill(ANSWER);
  out.tall = await measure();
  await setHeight(KEYBOARD_UP);
  out.typed = await measure();
  // the tap, at 508 with the answer at the room
  const c = { x: (out.typed.send.left + out.typed.send.right) / 2, y: (out.typed.send.top + out.typed.send.bottom) / 2 };
  out.tapAt = c;
  out.tapInFrame = c.y >= 0 && c.y <= out.typed.frameH && c.x >= 0 && c.x <= W;
  out.sentBefore = await page.evaluate((tid) => window.__wsSent.filter((f) => f.includes('"userTodoAnswer"') && f.includes(tid)).length, cfg.tid);
  if (cfg.tid2) out.otherTagged = await tagButton(cfg.tid2);
  if (out.tapInFrame) await page.mouse.click(c.x, c.y);
  await settle();
  await page.waitForTimeout(300);
  // the chat page's card is rebuilt by the pushes that follow the send (the pane's list gets none here): wait for the rebuild
  // before anything is located on the card, and record what came
  if (cfg.tid2 && cfg.pane === "chat" && out.otherTagged) out.rebuild = await waitForRebuild(cfg.tid2);
  out.after = await page.evaluate((tid) => ({
    overlayUp: !!document.getElementById("ut-reply-prompt"),
    rowUp: !!document.querySelector(`.ut-reply[data-tid="${tid}"]`),
    sent: window.__wsSent.filter((f) => f.includes('"userTodoAnswer"') && f.includes(tid)).map((f) => f.slice(0, 200)),
  }), cfg.tid);
  // the drag guard on the other todo's sheet: an inline height written as the resize grip writes it (the headless grip does
  // not move in every engine, so the write stands in for the pull), then one keystroke; the height the person set stands.
  // Its own failure is recorded, never fatal, so the composition's record above reaches the Python side whole: on a tree
  // where the tap missed, the composition's sheet is still up and covers the other todo's button
  if (cfg.tid2 && out.after.overlayUp) out.drag = { skipped: "the composition's sheet is still up after the tap" };
  else if (cfg.tid2) {
    try {
      await openReply(cfg.tid2);
      const at = await measure();
      await page.evaluate(() => { document.querySelector("#ut-reply-prompt .ut-reply-input").style.height = "150px"; });
      await settle();
      const dragged = await measure();
      await page.locator("#ut-reply-prompt .ut-reply-input").focus();
      await page.keyboard.type("a");
      await settle();
      const typed = await measure();
      out.drag = { openStyleH: at.inputStyleH, openH: at.inputH, draggedStyleH: dragged.inputStyleH, draggedH: dragged.inputH, afterKeyStyleH: typed.inputStyleH, afterKeyH: typed.inputH };
      // the detail's cap under the keyboard, on this sheet at open at 508 (the other todo: a short ask, no chips, the forty-line
      // detail, so the room would hold more than 12em): 12em, as before
      out.kbCap = { frameH: at.frameH, tight: at.tight, detailH: at.detailH, detailScrollH: at.detailScrollH, detailMaxH: at.detailMaxH, detailFontPx: at.detailFontPx };
    } catch (e) { out.drag = { error: String(e).slice(0, 400) }; }
    // the dragged height is a PREFERENCE clamped to the room (composition-3): written to 215px as the grip leaves it, it stands at
    // 508 (the room holds it); the frame at 420 clamps it to the room the box has, not to the content; back at 508 it returns to
    // 215. Recorded whole (the three measurements), its own failure recorded and never fatal
    if (!out.drag.error) {
      try {
        await page.evaluate(() => { document.querySelector("#ut-reply-prompt .ut-reply-input").style.height = "215px"; });
        await settle();
        const set = await measure();
        await setHeight(TIGHT);
        await waitTight(true);
        const clamped = await measure();
        await setHeight(KEYBOARD_UP);
        await waitTight(false);
        const back = await measure();
        out.pref = { set, clamped, back };
      } catch (e) { out.pref = { error: String(e).slice(0, 400) }; }
    }
    // a click whose press began inside the sheet is not a backdrop tap (composition-2, and the reviewer's ruling on the
    // selection): on the same sheet the grip is pulled past the box's bottom edge and released over the backdrop, then a text
    // selection is dragged from inside the box onto the backdrop; the sheet stands with its text after both, and a plain tap on
    // the backdrop then dismisses. Its own failure is recorded, never fatal, so the records above reach the Python side whole
    if (!out.drag.error) {
      try {
        out.release = await dragRelease();
        if (out.release.overlayUp) out.selectRelease = await selectRelease();
        if (out.release.overlayUp && out.selectRelease.overlayUp) {
          const at = { x: W / 2, y: Math.max(4, Math.round(out.release.boxTop / 2)) };
          await page.mouse.click(at.x, at.y);
          await settle();
          await page.waitForTimeout(200);
          out.backdropTap = { at, overlayUp: await page.evaluate(() => !!document.getElementById("ut-reply-prompt")) };
        }
      } catch (e) { out.release = { error: String(e).slice(0, 400) }; }
    }
  }
  // the stated boundary, on the third todo (a short ask and the recorded 8-line detail), at rest: whatever sheet the steps above
  // left up is cancelled first; opened at the app's 732, then resized under it (the resize re-runs restCap) to 720, one pixel
  // under this engine's own boundary, and Safari's common 633. Its own failure is recorded, never fatal
  if (cfg.tid3) {
    try {
      await page.evaluate(() => { const o = document.getElementById("ut-reply-prompt"); if (o) o.querySelector(".confirm-actions button").click(); });
      await page.waitForFunction(() => !document.getElementById("ut-reply-prompt"), null, { timeout: 10000 });
      await setHeight(APP_PANE, false);
      await openReply(cfg.tid3);
      const eight = { app: await measure() };
      await setHeight(BOUNDARY, false);
      eight.boundary = await measure();
      await setHeight(cfg.belowBoundary, false);
      eight.below = await measure();
      await setHeight(SAFARI_BARS, false);
      eight.safari = await measure();
      out.eight = eight;
    } catch (e) { out.eight = { error: String(e).slice(0, 400) }; }
  }
  // THE TOUCH ROAD (the maintainer's round 2, ui-1), in Chromium through the DevTools protocol's touch input (Playwright drives no
  // touch moves in Firefox or WebKit, where touch is a stated residual): a finger pressed just outside the box's left edge and
  // lifted just inside it, at the answer box's height, 6px out and 6px in, then 10px out and 5px in (the ruling's distances; at
  // the phone's width that press lies just past the window's left edge), at rest at 900 and with the keyboard up at 508; then a
  // finger's tap on the backdrop. A touch pointer is implicitly captured to the node it pressed, so
  // until the builders gave a backdrop press's capture back, the pointerup's target was the overlay wherever the finger lifted and
  // the straddle closed the sheet with the answer. On the third todo's sheet (the one the boundary step left up), the answer typed
  // before each gesture; a gesture that closed the sheet is recorded and the sheet reopened for the next. Its own failure is
  // recorded, never fatal
  if (cfg.tid3 && engine === "chromium") {
    try {
      const cdp = await context.newCDPSession(page);
      const at = (p) => [{ x: p.x, y: p.y, id: 1, radiusX: 1, radiusY: 1, force: 1 }];
      const touch = async (path) => {
        await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: at(path[0]) });
        for (let k = 1; k < path.length; k++) for (let s = 1; s <= 6; s++) {
          const a = path[k - 1], b = path[k];
          await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: at({ x: a.x + (b.x - a.x) * s / 6, y: a.y + (b.y - a.y) * s / 6 }) });
        }
        await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
        await settle(); await page.waitForTimeout(300);
      };
      const TYPED = "my typed answer";
      const state = () => page.evaluate((tid) => { const i = document.querySelector("#ut-reply-prompt .ut-reply-input");
        return { up: !!document.getElementById("ut-reply-prompt"), value: i ? i.value : null, sent: window.__wsSent.filter((f) => f.includes('"userTodoAnswer"') && f.includes(tid)).length }; }, cfg.tid3);
      const ready = async () => { if (!(await state()).up) await openReply(cfg.tid3); await fill(TYPED); };
      const points = () => page.evaluate(() => { const o = document.getElementById("ut-reply-prompt"), b = o.querySelector(".confirm-box").getBoundingClientRect(), i = o.querySelector(".ut-reply-input").getBoundingClientRect();
        return { boxLeft: b.left, inputY: (i.top + i.bottom) / 2, back: { x: (b.left + b.right) / 2, y: Math.max(4, b.top / 2) } }; });
      const touched = [];
      for (const [h, kb] of [[TALL, false], [KEYBOARD_UP, true]]) {
        await setHeight(h, kb);
        // the press on the backdrop left of the box at the ruling's distances, unclamped: at the phone's width the box's left edge
        // is under 8px from the window's, so the 10px press lies just past the window's left edge (x under 0), which the protocol
        // accepts and Chromium delivers to the overlay; the distance used is recorded
        for (const [out1, in1] of [[6, 6], [10, 5]]) {
          await ready();
          const p = await points();
          const x = p.boxLeft - out1;
          await touch([{ x, y: p.inputY }, { x: p.boxLeft + in1, y: p.inputY }]);
          touched.push({ h, out: +(p.boxLeft - x).toFixed(1), in: in1, at: p, ...(await state()) });
        }
      }
      await ready();
      const p = await points();
      await touch([p.back]);
      out.touch = { straddles: touched, tap: { h: KEYBOARD_UP, at: p.back, ...(await state()) } };
    } catch (e) { out.touch = { error: String(e).slice(0, 400) }; }
  }
  // THE WORST CASE (the maintainer's round 2 ruling, B-i), one cell per pane: a multi-line ask at the kernel's 300-character
  // cap (the tallest legal ask: the quoted line keeps its line breaks) with both chips and the linked forty-one-line detail,
  // opened at rest at the installed app's 732 and the keyboard then raised to 508 (the phone's order), fourteen lines typed and
  // a keystroke at their end, then a real click at Send's centre. The floors pass the box's cap there, so the box scrolls; at
  // a6e7f1cfa Send lay past the box's clip and the click closed the sheet with nothing sent, in both panes. Read: Send against
  // the box's clip (its padding box) and the page, what a finger at its centre reaches, the answer box against three rows, the
  // line being typed against the kept actions row, and what the click sent. The node legs drive the whole grid; this is the cell
  // CI executes. Whatever sheet the steps above left up is cancelled first. Its own failure is recorded, never fatal
  if (cfg.tidWorst) {
    try {
      await page.evaluate(() => { const o = document.getElementById("ut-reply-prompt"); if (o) o.querySelector(".confirm-actions button").click(); });
      await page.waitForFunction(() => !document.getElementById("ut-reply-prompt"), null, { timeout: 10000 });
      await setHeight(APP_PANE, false);
      await openReply(cfg.tidWorst);
      await setHeight(KEYBOARD_UP, true);
      await fill(ANSWER);
      await page.locator("#ut-reply-prompt .ut-reply-input").focus();
      await page.keyboard.press(engine === "webkit" ? "Meta+ArrowDown" : "Control+End");
      await page.keyboard.type(" ok");
      await settle();
      const m = await page.evaluate(() => {
        const o = document.getElementById("ut-reply-prompt"); if (!o) return null;
        const box = o.querySelector(".confirm-box"), input = o.querySelector(".ut-reply-input"), actions = o.querySelector(".confirm-actions");
        const send = actions.querySelectorAll("button")[1];
        const b = box.getBoundingClientRect(), sr = send.getBoundingClientRect(), ir = input.getBoundingClientRect();
        const clipTop = b.top + box.clientTop, clipBottom = clipTop + box.clientHeight;
        const cx = (sr.left + sr.right) / 2, cy = (sr.top + sr.bottom) / 2, at = document.elementFromPoint(cx, cy);
        const cs = getComputedStyle(input), lh = parseFloat(cs.lineHeight) || 18;
        const rowBottom = ir.bottom - parseFloat(cs.paddingBottom) - parseFloat(cs.borderBottomWidth);
        const probe = document.createElement("textarea"); probe.className = "ut-reply-input"; probe.rows = 3;
        probe.style.position = "fixed"; probe.style.top = "0"; probe.style.left = "0"; probe.style.width = "300px"; probe.style.visibility = "hidden";
        document.body.appendChild(probe); const floorH = probe.clientHeight; probe.remove();
        return { frameH: innerHeight, clipTop, clipBottom, sendTop: sr.top, sendBottom: sr.bottom, cx, cy,
          hit: at === send ? "target" : at === o ? "overlay" : at === box ? "box" : at ? (at.className || at.tagName).split(" ")[0] : "none",
          inputH: input.clientHeight, floorH, rowTop: rowBottom - lh, rowBottom, actionsTop: actions.getBoundingClientRect().top,
          boxScrollTop: box.scrollTop, over: box.scrollHeight - box.clientHeight };
      });
      const sentFor = () => page.evaluate((tid) => window.__wsSent.filter((f) => f.includes('"userTodoAnswer"') && f.includes(tid)).map((f) => { try { return JSON.parse(f).text; } catch (e) { return "(unparsed) " + f.slice(0, 120); } }), cfg.tidWorst);
      const sentBefore = (await sentFor()).length;
      const inFrame = !!m && m.cy >= 0 && m.cy <= m.frameH;
      if (inFrame) await page.mouse.click(m.cx, m.cy);
      await settle();
      await page.waitForTimeout(300);
      out.worst = { m, inFrame, typed: ANSWER + " ok", sentBefore, sent: await sentFor(), up: await page.evaluate(() => !!document.getElementById("ut-reply-prompt")) };
    } catch (e) { out.worst = { error: String(e).slice(0, 400) }; }
  }
  await result({ ready: true });
} catch (e) {
  await result({ died: String(e).slice(0, 600) });
}
