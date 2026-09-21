// The browser driver for tests/test_reply_sheet_served.py: the todo Reply sheet, as the kernel serves it in the Waiting
// pane (/waiting) and the chat page (/chat), on a phone with the keyboard up, against a hermetic lab kernel. The
// composition the maintainer's round 1 ruling on PR 859 asked for: at 390 by 508 (the pane's own innerHeight IS the
// keyboard's signal: inside the shell the pane iframe is sized to the visible height), a todo with a wrapped ask, a file
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
// a finger once the box is scrolled to it, Send inside the clip and under a finger at the box's bottom); at 420px with
// the same todo (the pane's two chip rows put the floors past the fold's cap, so its box scrolls a few pixels and Send's
// centre is under a finger; the chat's column fits); the detail's scrollWidth against its offsetWidth, the border box,
// with the unbreakable token wrapped (overflow-wrap: anywhere); the answer typed at 900px and the window then shrunk to
// 508 (kbFit re-runs grow on the resize: the answer box re-fits to the room). After the tap, on the other todo: an
// inline height written as the resize grip writes it, then one keystroke (the drag guard: the height stands); the height
// written to 215px and the frame taken to 420 and back (the dragged height is a preference: clamped to the room under the
// fold, not to the content, and returned to at 508); then the grip pulled past the box's bottom edge and released over the backdrop (the click that ends a drag of the grip is not a
// dismissal: the sheet stands with its text; Chromium and WebKit dispatch that click to the overlay, Firefox to the
// textarea), and a plain tap on the backdrop (it dismisses).
//
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
const W = 390, KEYBOARD_UP = 508, TIGHT = 420, SHORT = 300, TALL = 900;
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
const setHeight = async (h) => {
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
    box: rect(box), boxScrollH: box.scrollHeight, boxClientH: box.clientHeight, boxOverflowY: cs(box).overflowY,
    send: rect(send), cancel: rect(cancel), hitAtSend: hit(send), hitAtCancel: hit(cancel),
    kinds: Array.from(box.children).map((c) => (["wt-file", "wt-link", "ut-file", "ut-link"].find((k) => c.classList.contains(k)) || (c.className || c.tagName).split(" ")[0])),
    quoteChips: quote ? Array.from(quote.querySelectorAll(".ut-file, .ut-link")).map((c) => (c.classList.contains("ut-file") ? "ut-file" : "ut-link")) : [],
    inputSel: input.matches("#ut-reply-prompt .ut-reply-input"), detailSel: detail ? detail.matches("#ut-reply-prompt .ut-detail.open") : null, boxSel: box.matches("#ut-reply-prompt .picker-box"),
    // the answer box's sizing, for the record: its inline height (grow's last write), computed min-height and line-height,
    // and every child's laid-out height
    inputStyleH: input.style.height, inputMinH: cs(input).minHeight, inputLineH: cs(input).lineHeight, inputScrollH: input.scrollHeight,
    kids: Array.from(box.children).map((c) => [(["wt-file", "wt-link"].find((k) => c.classList.contains(k)) || (c.className || c.tagName).split(" ")[0]), +c.getBoundingClientRect().height.toFixed(1)]),
  };
});
// a short window, where the box itself may have to scroll: the detail against its floor, whether it scrolls, whether the
// address on its first line is under a finger once the box is scrolled to it, and Send at the box's bottom
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
  detail.scrollTop = 30; const detailScrolls = detail.scrollTop > 0; detail.scrollTop = 0;
  box.scrollTop = box.scrollHeight;
  const o = { frameH: window.innerHeight, tight: overlay.classList.contains("kb-tight"), alignItems: getComputedStyle(overlay).alignItems, paddingTop: getComputedStyle(overlay).paddingTop,
    detailH: detail.clientHeight, detailLineH: parseFloat(getComputedStyle(detail).lineHeight),
    detailScrolls, linkHit, boxScrollH: box.scrollHeight, boxClientH: box.clientHeight, boxScrollTop: box.scrollTop, sendHitAtBottom: hit(send), sendInBoxAtBottom: inBox(send) };
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
  const btn = page.locator(replySel).first();
  await btn.scrollIntoViewIfNeeded();
  await btn.click();
  await page.waitForSelector("#ut-reply-prompt .ut-reply-input", { timeout: 10000 });
  await settle();
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
  await openReply(cfg.tid);
  out.opened = await measure();
  // the short window: the fold on, the floors alone past the cap
  await setHeight(SHORT);
  await waitTight(true);
  out.short = await probeShort();
  // 420px with the same todo: the pane's two chip rows put the floors past the fold's cap (the box scrolls a few pixels; the
  // backstop state), the chat's column fits; at open and with fourteen lines typed
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
  await fill(ANSWER);
  out.tall = await measure();
  await setHeight(KEYBOARD_UP);
  out.typed = await measure();
  // the tap, at 508 with the answer at the room
  const c = { x: (out.typed.send.left + out.typed.send.right) / 2, y: (out.typed.send.top + out.typed.send.bottom) / 2 };
  out.tapAt = c;
  out.tapInFrame = c.y >= 0 && c.y <= out.typed.frameH && c.x >= 0 && c.x <= W;
  out.sentBefore = await page.evaluate((tid) => window.__wsSent.filter((f) => f.includes('"userTodoAnswer"') && f.includes(tid)).length, cfg.tid);
  if (out.tapInFrame) await page.mouse.click(c.x, c.y);
  await settle();
  await page.waitForTimeout(300);
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
    // the click that ends a grip drag is not a tap on the backdrop (composition-2): on the same sheet the grip is pulled past the
    // box's bottom edge and released over the backdrop; the sheet stands with its text, and a plain tap on the backdrop then
    // dismisses. Its own failure is recorded, never fatal, so the records above reach the Python side whole
    if (!out.drag.error) {
      try {
        out.release = await dragRelease();
        if (out.release.overlayUp) {
          const at = { x: W / 2, y: Math.max(4, Math.round(out.release.boxTop / 2)) };
          await page.mouse.click(at.x, at.y);
          await settle();
          await page.waitForTimeout(200);
          out.backdropTap = { at, overlayUp: await page.evaluate(() => !!document.getElementById("ut-reply-prompt")) };
        }
      } catch (e) { out.release = { error: String(e).slice(0, 400) }; }
    }
  }
  await result({ ready: true });
} catch (e) {
  await result({ died: String(e).slice(0, 600) });
}
