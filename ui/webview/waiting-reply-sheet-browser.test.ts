// The Waiting-on-you pane's Reply sheet on a phone with the keyboard up, in a real engine (the user 2026-09-19,
// screenshot): a todo's long detail filled the sheet and the answer box was one squeezed line above Cancel and Send.
// The sheet (waiting.ts showReply) is a column flex box capped at the window with overflow hidden; the detail, a
// wrapped text block, never shrinks (its automatic minimum is its content), the textarea shrinks to nothing (a
// textarea's resolves to zero), and the cap clips rather than scrolls. reply-sheet-keyboard.test.ts pins the rules
// and executes the fold and the grow handler against stand-ins; this leg lays the real thing out.
//
// THE COMPOSITION (the maintainer's round 1 ruling): the three rules of the fix were each right alone and failed
// together on the one viewport the fix exists for. At 390 by 508 with the keyboard up, a wrapped ask carrying both
// chips, a forty-line detail and an answer grown to the cap, the answer box (unshrinkable) grown to a share of the
// WINDOW laid Cancel and Send out below the bottom of the box, which above the fold's 480px was still overflow hidden;
// clipped content is not hit-testable, so a tap where Send was painted fell on the backdrop, and the backdrop's click
// closes the sheet: the typed answer was gone. The assembled sheet is now measured with a person's finger where Send
// is painted: Send and Cancel inside the box's clip and inside the frame, elementFromPoint at Send's centre IS Send,
// and a real click there sends (the userTodoAnswer message posted, the row removed) and does not close the sheet by
// the backdrop. On the round-1 tree that tap closed the sheet with nothing posted and the row still there (the
// figures are in the review record). The grow handler now caps the answer at the room the box has left, read from the
// box, and the box scrolls at every height (styles.css #ut-reply-prompt .picker-box), so the same is measured after
// the answer has grown and the window then shrinks (900 to 508 and to 420: kbFit re-runs grow on the resize), at 420
// under the fold, at 490 (the onset of the band where the shared box rule alone left the clip) with a todo that has
// no detail and a fourteen-line answer, and at 900.
//
// The browser legs (Chromium, Firefox, and WebKit when the box has them) load the kernel's /waiting page as it is
// served (styles.css, then the pane's sheet) with the worktree's waiting.ts bundle in a 390px-wide frame, the
// phone's width, and drive the frame's HEIGHT as the keyboard would: inside the shell the pane iframe is sized to the
// visible height (--app-h), so the frame's innerHeight IS the keyboard's signal and a shorter frame is the keyboard up.
// Three todos are fed: one with a short ask and a forty-line detail (the configuration that pins the detail's cap), one
// with a near-300-character ask, a file chip, a link chip and the detail (the composition fixture: without the chips
// and the wrapped ask the box never clipped at 508), and one with no detail. On the base tree the first red differs by
// engine (Chromium and WebKit: the answer box a 14px sliver; Firefox: the rows kept and the buttons clipped), and the
// detail's computed overflow-y, visible there, is the red common to all three. Where the legs skip (no playwright, no
// engine), the served leg tests/test_reply_sheet_served.py runs the same composition against the served pages in
// CI's browser step. Synthetic fixtures only: the notes-api world, a placeholder sid, TESTHOST, an invented path.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const PANE_CSS = fs.readFileSync(path.join(UI, "waiting-pane.css"), "utf8");
const STYLES_CSS = fs.readFileSync(path.join(UI, "styles.css"), "utf8");

// synthetic world: one session of the notes-api demo, three todos
const SID = "TESTHOST:11111111-2222-3333-4444-555555555555";
const NAME = "TESTHOST:api";
const TEXT = "Which layout should the quarterly report use?";
const DETAIL = Array.from({ length: 40 }, (_, i) => `Option ${i + 1}: the summary section leads and the tables follow, with the notes folded under each table.`).join("\n")
  + "\nreport-layout-" + "x".repeat(90);   // an unbreakable token wider than the sheet: without overflow-wrap it made the detail a sideways scroller
// the composition fixture: a wrapped ask near the 300-character cap the kernel enforces, a file, an address, and a detail
// whose first line carries an address (the link the detail keeps reachable)
const LONG_TEXT = "Which layout should the quarterly report use for the regional tables, the summary section and the appendix, given that the notes under each table now run to several lines and the reviewers asked for the totals to lead every page rather than close it?";
const FILE = "/srv/notes-api/docs/quarterly-report-layout.md";
const LINK = "https://github.com/example-org/notes-api/pull/398";
const LINKED_DETAIL = "The earlier draft is at https://github.com/example-org/notes-api/pull/398 and the reviewers' notes follow.\n" + DETAIL;
const TODOS = [
  { id: "t1", text: TEXT, detail: DETAIL },
  { id: "t2", text: LONG_TEXT, detail: LINKED_DETAIL, file: FILE, link: LINK },
  { id: "t3", text: TEXT },
];
const ANSWER = (n: number) => Array.from({ length: n }, (_, i) => `line ${i + 1}`).join("\n");
const PHONE_W = 390;
const KEYBOARD_UP = 508;   // above the fold's threshold: the squeeze fix alone
const KEYBOARD_TIGHT = 420;   // under it: the fold too
const ONSET = 490;   // the shared box rule's clip band began here (extra9-2's refuter): above the fold, under the old clip
const TALL = 900;

function bundle(entry: string): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, entry)], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the frame the pane runs in, at the phone's width; its height is the test's input (the shell's --app-h sizing)
const SHELL_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8>
<style>body{margin:0}iframe{display:block;width:${PHONE_W}px;height:${KEYBOARD_UP}px;border:0}</style></head><body>
<iframe id=f-waiting src=/waiting></iframe></body></html>`;
// the kernel's /waiting page, as _waiting_page serves it: the chat's stylesheet, then the pane's sheet in a <style>
// after it (the sheet's @import and font urls 404 here, harmlessly). The served shim's acquireVsCodeApi is a recorder
// here: every postMessage the pane makes is kept on the frame's window, so a Send is observable as the message it posts
const WAITING_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><link href=/dist/styles.css rel=stylesheet>
<style>${PANE_CSS}</style></head><body>
<div id=waiting-head></div><div id=waiting-list></div>
<script>window.__posted=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posted.push(m);},getState:function(){return null;},setState:function(){}}};</script>
<script src=/dist/waiting.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Rect = { top: number; bottom: number; left: number; right: number };
// the sheet's geometry, read in the frame: the frame's height, the fold, the overlay's placement, the answer box's
// height against a three-row probe, the detail's scroll state, the box's edges and scroll state, the two buttons' rects
// and what a finger at each one's centre would reach (elementFromPoint), and the box's children by their first class
type Sheet = {
  frameH: number; tight: boolean; alignItems: string; paddingTop: string;
  inputH: number; floorH: number; lineHeight: string; inputOverflowY: string; inputStyleH: string;
  detailScrollH: number; detailClientH: number; detailOverflowY: string; detailLineH: number; detailFontPx: number; detailScrolls: boolean;
  detailTextRight: number; detailRight: number; detailOverflowX: string;
  actionsBottom: number; boxTop: number; boxBottom: number; boxScrollH: number; boxClientH: number; boxOverflowY: string;
  sendRect: Rect; cancelRect: Rect; hitAtSend: string; hitAtCancel: string; kinds: string[];
};
// a short window, where the box itself must scroll: the detail's height against its floor (two of its lines), whether it
// scrolls within itself, whether the address on its first line is under a finger once the box is scrolled to it, and
// whether Send is inside the clip and under a finger once the box is scrolled to its bottom
type Short = {
  frameH: number; tight: boolean; detailH: number; detailLineH: number; detailScrolls: boolean; linkHit: string;
  boxScrollH: number; boxClientH: number; boxScrollTop: number; sendHitAtBottom: string; sendInBoxAtBottom: boolean;
};
const floorOf = (lineH: number) => 2 * lineH - 1;   // two lines, less a pixel of rounding
const rectOf = (r: Rect) => `${r.top.toFixed(1)}..${r.bottom.toFixed(1)}`;
const centre = (r: Rect) => ({ x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2 });

async function boot(browser: any) {
  const errors: string[] = [];
  const waitingJs = bundle("waiting.ts");
  const page = await browser.newPage({ viewport: { width: PHONE_W + 30, height: TALL + 40 } });
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await page.route("http://romp.test/**", (route: any) => {
    const u = new URL(route.request().url());
    if (u.pathname === "/shell") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: SHELL_HTML });
    if (u.pathname === "/waiting") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: WAITING_HTML });
    if (u.pathname === "/dist/waiting.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: waitingJs });
    if (u.pathname === "/dist/styles.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: STYLES_CSS });
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto("http://romp.test/shell");   // the load event covers the frame's boot
  await page.evaluate(([sid, name, todos]: [string, string, typeof TODOS]) => {
    const f = document.getElementById("f-waiting") as HTMLIFrameElement;
    const now = Math.floor(Date.now() / 1000);
    f.contentWindow!.postMessage({ type: "feed", now, userTodosOn: true, userTodoRows: [{ sid, name, color: { bg: "#123456", fg: "#ffffff" },
      todos: todos.map((t, i) => ({ id: t.id, text: t.text, createdT: now - 300 + i, ...(t.detail ? { detail: t.detail } : {}), ...(t.file ? { file: t.file } : {}), ...(t.link ? { link: t.link } : {}) })) }] }, "*");
  }, [SID, NAME, TODOS] as [string, string, typeof TODOS]);
  const W = page.frameLocator("#f-waiting");
  await W.locator(`.ut-reply[data-tid="t1"]`).waitFor({ timeout: 10000 });
  // two animation frames in the FRAME's window: a resize handler runs at the frame after the size changed, and grow's
  // writes need a layout before they are read
  const settle = () => page.evaluate(() => new Promise<void>((r) => { const w = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!; w.requestAnimationFrame(() => w.requestAnimationFrame(() => r())); }));
  // the keyboard: the frame's height, and the frame's window sees it as its own resize
  const setHeight = async (h: number) => {
    await page.evaluate((hh: number) => { (document.getElementById("f-waiting") as HTMLIFrameElement).style.height = hh + "px"; }, h);
    await page.waitForFunction((hh: number) => (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.innerHeight === hh, h, { timeout: 10000 });
    await settle();
  };
  const measure = (): Promise<Sheet | null> => page.evaluate(() => {
    const win = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!;
    const d = win.document;
    const overlay = d.getElementById("ut-reply-prompt");
    if (!overlay) return null;
    const box = overlay.querySelector(".confirm-box") as HTMLElement;
    const input = overlay.querySelector(".ut-reply-input") as HTMLTextAreaElement;
    const detail = overlay.querySelector(".ut-detail") as HTMLElement | null;
    const actions = overlay.querySelector(".confirm-actions") as HTMLElement;
    const [cancel, send] = Array.from(actions.querySelectorAll("button")) as HTMLElement[];
    const cs = (e: Element) => win.getComputedStyle(e);
    const rect = (e: Element) => { const r = e.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, left: r.left, right: r.right }; };
    // what a finger at an element's painted centre reaches: the element itself, the overlay (the backdrop, whose click
    // closes the sheet), the box, another element by its first class or tag, or nothing (outside the frame)
    const hit = (e: HTMLElement) => {
      const r = e.getBoundingClientRect(); const at = d.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2);
      return at === e ? "target" : at === overlay ? "overlay" : at === box ? "box" : at ? ((at as HTMLElement).className || at.tagName).split(" ")[0] : "none";
    };
    // the three-row height in THIS engine: a probe of the same class, rows=3, laid out outside the sheet and OUT OF FLOW
    // (position fixed: the pane's body is a full-height flex column, and a probe in flow there is a shrinkable flex item
    // on a short frame, the very squeeze under test); measured and removed
    const probe = d.createElement("textarea"); probe.className = "ut-reply-input"; probe.rows = 3;
    probe.style.position = "fixed"; probe.style.top = "0"; probe.style.left = "0"; probe.style.width = "300px"; probe.style.visibility = "hidden";
    d.body.appendChild(probe);
    const floorH = probe.clientHeight;
    probe.remove();
    return {
      frameH: win.innerHeight, tight: overlay.classList.contains("kb-tight"), alignItems: cs(overlay).alignItems, paddingTop: cs(overlay).paddingTop,
      inputH: input.clientHeight, floorH, lineHeight: cs(input).lineHeight, inputOverflowY: cs(input).overflowY, inputStyleH: input.style.height,
      detailScrollH: detail ? detail.scrollHeight : 0, detailClientH: detail ? detail.clientHeight : 0, detailOverflowY: detail ? cs(detail).overflowY : "",
      detailLineH: detail ? parseFloat(cs(detail).lineHeight) : 0, detailFontPx: detail ? parseFloat(cs(detail).fontSize) : 0,
      // the widest line of the detail's text against the detail's own right edge: an unbreakable token that does not wrap
      // runs far past it (a sideways scroller); scrollWidth is not the measure, since a classic vertical scrollbar (WebKit
      // headless) sits inside the padding box and reports as sideways overflow whatever the text does
      detailTextRight: detail ? ((): number => { const rg = d.createRange(); rg.selectNodeContents(detail); return Array.from(rg.getClientRects()).reduce((w, x) => Math.max(w, x.right), 0); })() : 0,
      detailRight: detail ? detail.getBoundingClientRect().right : 0, detailOverflowX: detail ? cs(detail).overflowX : "",
      // the overflow declaration, live: a scroll container's scrollTop moves; with overflow visible it stays at 0
      detailScrolls: detail ? ((): boolean => { detail.scrollTop = 30; const moved = detail.scrollTop > 0; detail.scrollTop = 0; return moved; })() : false,
      actionsBottom: actions.getBoundingClientRect().bottom, boxTop: box.getBoundingClientRect().top, boxBottom: box.getBoundingClientRect().bottom,
      boxScrollH: box.scrollHeight, boxClientH: box.clientHeight, boxOverflowY: cs(box).overflowY,
      sendRect: rect(send), cancelRect: rect(cancel), hitAtSend: hit(send), hitAtCancel: hit(cancel),
      kinds: Array.from(box.children).map((c) => (["wt-file", "wt-link", "ut-file", "ut-link"].find((k) => c.classList.contains(k)) || (c.className || c.tagName).split(" ")[0])),
    };
  });
  const probeShort = (): Promise<Short> => page.evaluate(() => {
    const win = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!;
    const d = win.document;
    const overlay = d.getElementById("ut-reply-prompt")!;
    const box = overlay.querySelector(".confirm-box") as HTMLElement;
    const detail = overlay.querySelector(".ut-detail") as HTMLElement;
    const send = overlay.querySelectorAll(".confirm-actions button")[1] as HTMLElement;
    const hit = (e: HTMLElement) => {
      const r = e.getBoundingClientRect(); const at = d.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2);
      return at === e ? "target" : at === overlay ? "overlay" : at === box ? "box" : at ? ((at as HTMLElement).className || at.tagName).split(" ")[0] : "none";
    };
    const inBox = (e: Element) => { const r = e.getBoundingClientRect(), b = box.getBoundingClientRect(); return r.top >= b.top - 0.5 && r.bottom <= b.bottom + 0.5; };
    box.scrollTop = 0; detail.scrollTop = 0;
    detail.scrollIntoView({ block: "nearest" });   // the box scrolls the detail into view, as a finger would
    const a = detail.querySelector("a") as HTMLElement | null;
    // the address wraps at the phone's width, so the finger goes to the centre of its FIRST line fragment, not of the
    // union rect (whose centre can fall between the fragments)
    const first = a ? (a.getClientRects()[0] || a.getBoundingClientRect()) : null;
    const atLink = first ? d.elementFromPoint((first.left + first.right) / 2, (first.top + first.bottom) / 2) : null;
    const linkHit = !a ? "no-link" : atLink === a ? "target" : atLink ? ((atLink as HTMLElement).className || atLink.tagName).split(" ")[0] : "none";
    detail.scrollTop = 30; const detailScrolls = detail.scrollTop > 0; detail.scrollTop = 0;
    box.scrollTop = box.scrollHeight;   // to the bottom, where the buttons are
    const out = { frameH: win.innerHeight, tight: overlay.classList.contains("kb-tight"), detailH: detail.clientHeight, detailLineH: parseFloat(win.getComputedStyle(detail).lineHeight),
      detailScrolls, linkHit, boxScrollH: box.scrollHeight, boxClientH: box.clientHeight, boxScrollTop: box.scrollTop, sendHitAtBottom: hit(send), sendInBoxAtBottom: inBox(send) };
    box.scrollTop = 0;
    return out;
  });
  const openReply = async (tid: string) => {
    await W.locator(`.ut-reply[data-tid="${tid}"]`).click();
    await W.locator("#ut-reply-prompt .ut-reply-input").waitFor({ timeout: 10000 });
    await settle();
  };
  const cancelReply = async () => {
    await W.locator("#ut-reply-prompt .confirm-actions button").first().click();
    await page.waitForFunction(() => !(document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document.getElementById("ut-reply-prompt"), null, { timeout: 10000 });
  };
  const fill = async (text: string) => { await W.locator("#ut-reply-prompt .ut-reply-input").fill(text); await settle(); };
  const waitTight = (on: boolean) => page.waitForFunction((want: boolean) => {
    const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
    return d.getElementById("ut-reply-prompt")?.classList.contains("kb-tight") === want;
  }, on, { timeout: 10000 });
  // the tap: a real click at Send's painted centre, in the frame's coordinates (the frame sits at the page's origin), then
  // what the sheet did: is the overlay still up, is the todo's row still there, what was posted
  const tapSend = async (tid: string) => {
    const m = (await measure())!;
    const c = centre(m.sendRect);
    const inFrame = c.y >= 0 && c.y <= m.frameH && c.x >= 0 && c.x <= PHONE_W;
    if (inFrame) await page.mouse.click(c.x, c.y);
    await settle();
    const after: { overlayUp: boolean; rowUp: boolean; posted: Array<{ type: string; id: string; todoId: string; text: string }> } = await page.evaluate((t: string) => {
      const win = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow! as any;
      const d = win.document;
      return { overlayUp: !!d.getElementById("ut-reply-prompt"), rowUp: !!d.querySelector(`.ut-reply[data-tid="${t}"]`),
               posted: (win.__posted || []).filter((p: any) => p && p.type === "userTodoAnswer").map((p: any) => ({ type: p.type, id: p.id, todoId: p.todoId, text: String(p.text).slice(0, 40) })) };
    }, tid);
    return { before: m, tapAt: c, inFrame, ...after };
  };
  // the person pulls the box taller: a native drag of the resize grip (the textarea's bottom-right corner, inside the
  // border; resize: vertical), and where the headless engine's grip does not move (WebKit, in the round-1 refuters'
  // runs) the inline height written as the grip writes it; the road taken is reported with the result
  const dragTaller = async () => {
    const before = (await measure())!;
    const r = await page.evaluate(() => {
      const win = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!;
      const b = win.document.querySelector("#ut-reply-prompt .ut-reply-input")!.getBoundingClientRect();
      return { right: b.right, bottom: b.bottom };
    });
    await page.mouse.move(r.right - 5, r.bottom - 5);
    await page.mouse.down();
    await page.mouse.move(r.right - 5, r.bottom + 40, { steps: 8 });
    await page.mouse.move(r.right - 5, r.bottom + 60, { steps: 4 });
    await page.mouse.up();
    await settle();
    let m = (await measure())!;
    let road = "native grip";
    if (m.inputStyleH === before.inputStyleH || m.inputH <= before.inputH + 10) {
      road = "scripted (the headless grip did not move)";
      await page.evaluate(() => { const win = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!; (win.document.querySelector("#ut-reply-prompt .ut-reply-input") as HTMLElement).style.height = "150px"; });
      await settle();
      m = (await measure())!;
    }
    return { road, dragged: m };
  };
  return { page, W, setHeight, settle, measure, probeShort, openReply, cancelReply, fill, tapSend, dragTaller, waitTight, errors };
}
// a short window with the chip todo open: the box scrolls; the detail keeps its floor and scrolls within itself; its
// first line's address and Send are each under a finger once the box is scrolled to them
function assertShort(s: Short, what: string) {
  const rec = JSON.stringify(s);
  assert.equal(s.tight, true, `${what}: under the fold (${rec})`);
  assert.ok(s.detailH >= floorOf(s.detailLineH), `${what}: the detail keeps its floor of two lines (${s.detailH}px against a ${s.detailLineH}px line); without the floor it resolved to 0px, invisible and unscrollable (${rec})`);
  assert.ok(s.detailScrolls, `${what}: the detail scrolls within itself (${rec})`);
  assert.equal(s.linkHit, "target", `${what}: the address on the detail's first line is under a finger once the box is scrolled to it (${rec})`);
  assert.ok(s.boxScrollH > s.boxClientH + 1 && s.boxScrollTop > 0, `${what}: the box scrolls: the floors alone overflow this window, and the deficit past them is a scroll of the box, never a clip (${rec})`);
  assert.ok(s.sendInBoxAtBottom && s.sendHitAtBottom === "target", `${what}: scrolled to the box's bottom, Send is inside the clip and under a finger (${rec})`);
}

// Send is INSIDE the box's clip (its rect within the box's rect) and inside the frame, so a finger on it reaches it. The
// box's rect is its clip: overflow hidden or auto, content past its edges is not hit-testable
const sendInsideBox = (m: Sheet) => m.sendRect.top >= m.boxTop - 0.5 && m.sendRect.bottom <= m.boxBottom + 0.5;
const cancelInsideBox = (m: Sheet) => m.cancelRect.top >= m.boxTop - 0.5 && m.cancelRect.bottom <= m.boxBottom + 0.5;
const boxInsideFrame = (m: Sheet) => m.boxTop >= -0.5 && m.boxBottom <= m.frameH + 0.5;
const where = (m: Sheet) => `Send ${rectOf(m.sendRect)}, Cancel ${rectOf(m.cancelRect)}, box ${m.boxTop.toFixed(1)}..${m.boxBottom.toFixed(1)} (${m.boxClientH} of ${m.boxScrollH}px, overflow-y ${m.boxOverflowY}), frame ${m.frameH}px, input ${m.inputH}px (floor ${m.floorH}), detail ${m.detailClientH} of ${m.detailScrollH}px`;
// the buttons are reachable: their bottom edge is inside the frame, or the box itself scrolls to them (the every-height
// overflow-y: auto backstop for a window too short for the whole sheet)
const reachable = (m: Sheet) => m.actionsBottom <= m.frameH + 0.5 || (m.boxOverflowY === "auto" && m.boxScrollH > m.boxClientH + 1);
// the answer grown to the room: nothing clipped, Send and Cancel inside the clip and the frame, a finger reaches Send
function assertFits(m: Sheet, what: string) {
  assert.ok(boxInsideFrame(m), `${what}: the box is inside the frame (${where(m)})`);
  assert.ok(sendInsideBox(m) && cancelInsideBox(m), `${what}: Cancel and Send are inside the box's clip (${where(m)})`);
  assert.ok(m.boxScrollH <= m.boxClientH + 1, `${what}: the box's content fits its cap, so nothing is a scroll away (${where(m)})`);
  assert.equal(m.hitAtSend, "target", `${what}: a finger at Send's painted centre reaches Send (${where(m)})`);
  assert.equal(m.hitAtCancel, "target", `${what}: a finger at Cancel's painted centre reaches Cancel (${where(m)})`);
}

for (const name of ["chromium", "firefox", "webkit"]) {
  test(`in ${name}: with the keyboard up the answer box holds three rows, the detail scrolls within its cap, and Cancel and Send stay in the frame; the fold follows the frame's height; a tap where Send is painted sends`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension, and the browser legs need it; the served leg tests/test_reply_sheet_served.py runs this composition in CI's browser step"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box, and this leg needs it; the served leg tests/test_reply_sheet_served.py is the guard where this skips (CI's browser step runs it in chromium): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { page, W, setHeight, settle, measure, probeShort, openReply, cancelReply, fill, tapSend, dragTaller, waitTight, errors } = await boot(browser);
      await openReply("t1");
      // ── 508px: the keyboard up on a phone, above the fold's threshold — the squeeze fix alone
      let m = (await measure())!;
      assert.ok(m, "the Reply sheet is up");
      assert.equal(m.frameH, KEYBOARD_UP, "the frame is the phone's visible height with the keyboard up");
      assert.equal(m.tight, false, "508px is not a short window: no fold, so what follows is the squeeze fix on its own");
      assert.ok(m.floorH > 30, `the probe laid out three rows (${m.floorH}px; line-height ${m.lineHeight})`);
      assert.ok(m.inputH >= m.floorH - 1, `the answer box holds three rows: ${m.inputH}px against the ${m.floorH}px three-row probe (on the base tree it was a 14px sliver in Chromium and WebKit, the textarea taking the whole deficit; Firefox kept the rows there and the detail's overflow-y assertion below is the base tree's red in all three engines)`);
      assert.equal(m.detailOverflowY, "auto", "the detail scrolls within itself (the base tree computes visible in Chromium, Firefox and WebKit alike: the red common to the three engines, reached first in Firefox, where the textarea kept its rows and the buttons were clipped instead)");
      assert.ok(m.detailScrolls, "the overflow declaration is LIVE: the detail's scrollTop moves (with overflow visible it stays at 0, and the detail's text paints over the answer box); the rule pin reads the sheet with comments stripped, this reads the engine");
      assert.ok(m.detailScrollH > m.detailClientH + 8, `the forty-line detail overflows its cap and is a scroll away, not clipped (${m.detailClientH} of ${m.detailScrollH}px)`);
      assert.ok(m.detailTextRight <= m.detailRight + 0.5, `no sideways scroller: the unbreakable token in the detail wraps inside the box (overflow-wrap: anywhere; the widest line ends at ${m.detailTextRight.toFixed(1)}, the detail at ${m.detailRight.toFixed(1)}px); without the wrap the token ran hundreds of pixels past it and a scroll container's overflow-x, computing to auto, scrolled sideways`);
      assert.equal(m.detailOverflowX, "hidden", "overflow-x: hidden, #pinned-notes's companion declaration, so a token the wrap cannot break is clipped, never a sideways scroll");
      assert.ok(m.detailClientH > 20, `the detail still shows some lines (${m.detailClientH}px): the box gave way, not the whole detail`);
      assert.ok(m.actionsBottom > 0 && m.actionsBottom <= m.frameH + 0.5, `Cancel and Send are inside the frame (bottom edge ${m.actionsBottom.toFixed(1)} of ${m.frameH}px)`);
      assert.ok(m.boxBottom <= m.frameH + 0.5, `the whole box is inside the frame (${m.boxBottom.toFixed(1)} of ${m.frameH}px)`);
      assert.equal(m.boxOverflowY, "auto", "the box scrolls at this height too, not only under the fold: the every-height backstop (#ut-reply-prompt .picker-box)");
      // ── 420px: a short window — the fold, on the frame's own resize event
      await setHeight(KEYBOARD_TIGHT);
      await waitTight(true);
      m = (await measure())!;
      assert.equal(m.tight, true, "under 480px the sheet wears kb-tight");
      assert.equal(m.alignItems, "flex-start", "folded, the sheet sits at the top rather than centering into the keyboard");
      assert.equal(m.paddingTop, "12px", "under the picker's 12px frame");
      assert.ok(m.inputH >= m.floorH - 1, `folded, the answer box still holds three rows (${m.inputH} against ${m.floorH}px)`);
      assert.ok(m.detailScrollH > m.detailClientH + 8, `folded, the detail still scrolls within itself (${m.detailClientH} of ${m.detailScrollH}px)`);
      assert.ok(reachable(m), `folded, the buttons are reachable (bottom edge ${m.actionsBottom.toFixed(1)} of ${m.frameH}px; box ${m.boxClientH} of ${m.boxScrollH}px, overflow-y ${m.boxOverflowY})`);
      assert.ok(m.boxClientH <= KEYBOARD_TIGHT - 24 + 1, `the box is capped at the visible height less the 12px frame (${m.boxClientH}px)`);
      // ── typing: the box grows with the answer, capped at the room the box has left, so the buttons stay inside the box's
      // clip and the frame; cleared, it returns to the floor
      const before = m.inputH;
      await fill(ANSWER(12));
      m = (await measure())!;
      assert.ok(m.inputH > before + 20, `twelve lines grow the box (${before} → ${m.inputH}px)`);
      assertFits(m, "folded, the answer grown");
      assert.ok(m.detailClientH >= floorOf(m.detailLineH), `folded, the answer grown: the detail keeps its floor of two lines (${m.detailClientH}px against a ${m.detailLineH}px line); the deficit state, which round 1 never measured`);
      await fill("");
      m = (await measure())!;
      assert.ok(Math.abs(m.inputH - before) <= 2, `cleared, the box is back at the floor (${m.inputH} vs ${before}px)`);
      // ── 900px: the keyboard down — the same event takes the fold off
      await setHeight(TALL);
      await waitTight(false);
      m = (await measure())!;
      assert.equal(m.tight, false, "the room back, the fold comes off");
      assert.notEqual(m.alignItems, "flex-start", "the sheet centers again (.confirm-overlay)");
      assert.ok(m.inputH >= m.floorH - 1, `tall, the answer box holds three rows (${m.inputH} against ${m.floorH}px)`);
      assert.ok(m.actionsBottom <= m.frameH + 0.5, "the buttons are inside the frame");
      // the cap at rest, where nothing squeezes: 12em of the detail's own font (about eight and a half lines), the whole of it
      // executed rather than a spelling; the keyboard-up heights above are the shrink and the floor, not this cap
      assert.ok(Math.abs(m.detailClientH - 12 * m.detailFontPx) <= 1.5, `tall, the forty-line detail sits at its cap: ${m.detailClientH}px against 12em of its ${m.detailFontPx}px font (${(12 * m.detailFontPx).toFixed(1)}px)`);
      // ── the answer grown TALL, then the keyboard: the window shrinks under an answer already grown, and the resize re-fits it
      // to the room the smaller box has (the cap's stated purpose; no leg measured it in round 1)
      await fill(ANSWER(14));
      m = (await measure())!;
      const grownTall = m.inputH;
      assert.ok(grownTall > m.floorH + 60, `at 900px fourteen lines grow the box well past the floor (${grownTall}px against ${m.floorH})`);
      assertFits(m, "tall, the answer grown");
      await setHeight(KEYBOARD_UP);
      m = (await measure())!;
      assert.ok(m.inputH < grownTall, `the window shrunk to 508px re-fits the answer box (${grownTall} → ${m.inputH}px): grow ran on the resize`);
      assert.ok(m.inputH >= m.floorH - 1, `and never under three rows (${m.inputH} against ${m.floorH}px)`);
      assertFits(m, "900 then 508, the answer grown");
      await setHeight(KEYBOARD_TIGHT);
      await waitTight(true);
      m = (await measure())!;
      assert.ok(m.inputH >= m.floorH - 1, `then 420px, folded: three rows still (${m.inputH} against ${m.floorH}px)`);
      assertFits(m, "900 then 420, the answer grown");
      await fill("");
      // ── the person pulls the box taller, then types ONE character: the dragged height stands. Before the guard every
      // keystroke snapped a dragged box back to its content's height, on a textarea whose own CSS invites the drag
      // (resize: vertical); the guard is file-comments.ts autosize's, copied into grow
      await setHeight(TALL);
      await waitTight(false);
      const d = await dragTaller();
      t.diagnostic(`${name}: the drag road was ${d.road}; inline height after the drag ${d.dragged.inputStyleH}, box ${d.dragged.inputH}px against the ${m.floorH}px floor`);
      assert.ok(d.dragged.inputH > m.floorH + 30, `the drag took (${d.road}): ${d.dragged.inputH}px against the ${m.floorH}px floor, inline height ${d.dragged.inputStyleH}`);
      await W.locator("#ut-reply-prompt .ut-reply-input").focus();
      await page.keyboard.type("a");
      await settle();
      m = (await measure())!;
      assert.equal(m.inputStyleH, d.dragged.inputStyleH, `one keystroke after the drag (${d.road}): the inline height the person set stands, grow stood down (before the guard it snapped back to the floor: ${m.inputH}px)`);
      assert.ok(m.inputH >= d.dragged.inputH - 1, `and the box keeps the dragged height (${m.inputH} against ${d.dragged.inputH}px)`);
      await setHeight(KEYBOARD_UP);
      await waitTight(false);
      await cancelReply();
      // ── THE COMPOSITION, at 390 by 508 with the keyboard up: the ask wrapped to several lines, both chips, the forty-line
      // detail, the answer grown to the cap: the state in which the round-1 tree laid Send out below the box's clip
      await openReply("t2");
      m = (await measure())!;
      assert.deepEqual(m.kinds, ["confirm-title", "confirm-detail", "wt-file", "wt-link", "ut-detail", "ut-reply-input", "confirm-actions"], "the pane's sheet with both chips as flex children of the box (waiting.ts showReply; the chat's builder puts them inside the quoted line)");
      assert.equal(m.tight, false, "508px: no fold");
      assert.ok(m.inputH >= m.floorH - 1, `with the chips and the wrapped ask the answer box holds three rows (${m.inputH} against ${m.floorH}px)`);
      // ── short windows with this sheet up, the floors alone past the box's cap: 300px (a short portrait phone under the
      // keyboard) and 230px (a landscape phone). The detail keeps two lines, the box scrolls to the rest
      await setHeight(300);
      await waitTight(true);
      assertShort(await probeShort(), "300px, the chip todo");
      await setHeight(230);
      assertShort(await probeShort(), "230px, the chip todo");
      await setHeight(KEYBOARD_UP);
      await waitTight(false);
      await fill(ANSWER(14));
      const tap = await tapSend("t2");
      const rec = JSON.stringify({ tapAt: tap.tapAt, inFrame: tap.inFrame, hitAtSend: tap.before.hitAtSend, sendRect: tap.before.sendRect, box: [tap.before.boxTop, tap.before.boxBottom, tap.before.boxClientH, tap.before.boxScrollH, tap.before.boxOverflowY], inputH: tap.before.inputH, detailH: tap.before.detailClientH, detailLineH: tap.before.detailLineH, after: { overlayUp: tap.overlayUp, rowUp: tap.rowUp, posted: tap.posted } });
      assert.ok(tap.before.detailClientH >= floorOf(tap.before.detailLineH), `composition: with the answer grown to the cap the detail keeps its floor of two lines (${tap.before.detailClientH}px against a ${tap.before.detailLineH}px line); on the round-1 tree it resolved to 0px here (${rec})`);
      assert.ok(boxInsideFrame(tap.before), `composition: the box is inside the frame (${where(tap.before)})`);
      assert.ok(sendInsideBox(tap.before) && cancelInsideBox(tap.before), `composition: Cancel and Send are inside the box's clip (${where(tap.before)}); on the round-1 tree the answer box grown to 40% of the window laid them out below it`);
      assert.equal(tap.before.hitAtSend, "target", `composition: a finger at Send's painted centre reaches Send, not the backdrop (${rec})`);
      assert.ok(tap.inFrame, `composition: the tap point is inside the frame (${rec})`);
      assert.deepEqual(tap.posted.map((p) => [p.type, p.todoId, p.text.split("\n")[0]]), [["userTodoAnswer", "t2", "line 1"]], `composition: the tap SENT the answer (one userTodoAnswer posted); on the round-1 tree it fell on the backdrop and posted nothing (${rec})`);
      assert.equal(tap.rowUp, false, `composition: the answered todo's row is gone (dropTodo: the send happened, not a backdrop close) (${rec})`);
      assert.equal(tap.overlayUp, false, `composition: the sheet closed by the send itself (${rec})`);
      // ── the onset of the old clip band, 490px, a todo with no detail and a fourteen-line answer: the room cap and the box's
      // scroll hold with nothing to shrink
      await setHeight(ONSET);
      await openReply("t3");
      m = (await measure())!;
      assert.deepEqual(m.kinds, ["confirm-title", "confirm-detail", "ut-reply-input", "confirm-actions"], "no detail, no chips: the sheet's smallest tree");
      await fill(ANSWER(14));
      m = (await measure())!;
      assert.ok(m.inputH > m.floorH + 20, `490px, no detail: fourteen lines grow the box (${m.inputH} against ${m.floorH}px)`);
      assertFits(m, "490px, no detail, the answer grown");
      await cancelReply();
      assert.deepEqual(errors, [], "no script error in the frame");
    } finally { await browser.close(); }
  });
}
