// The chat pane's Reply sheet (render.ts showUserTodoReply; waiting.ts showReply is the Waiting pane's builder) on a
// phone with the keyboard up, in a real engine (the user 2026-09-19, screenshot; waiting-reply-sheet-browser.test.ts
// is the pane's leg, reply-sheet-keyboard.test.ts the rules and the executed closures). The chat page loads styles.css
// alone, and render.ts is not bundled for a test page; so the sheet in the page is the REAL builder's output:
// showUserTodoReply and the two chip builders are lifted out of render.ts by name (the render-todo-file-chip.test.ts
// idiom) and bundled with the modules they import (path-links, url-links), the other names they read from render.ts's
// scope handed in as stand-ins (el; the URL pass alone for the two path linkers and nothing for the PR-ref linker, since
// paths and PR refs are not under test; a vscodeApi that RECORDS every postMessage on the window, so a Send is
// observable as the message it posts). The builder's own kbFit, grow, close, go and the backdrop's click run as written.
//
// THE COMPOSITION (the maintainer's round 1 ruling): at 390 by 508 with the keyboard up, a wrapped ask carrying both
// chips inside the quoted line, a forty-line detail and an answer grown to the cap, the round-1 tree laid Cancel and
// Send out below the box's clip (the answer box grown to a share of the WINDOW, the box overflow hidden above the fold's
// 480px); clipped content is not hit-testable, so a tap where Send was painted fell on the backdrop, whose click closes
// the sheet: the typed answer was gone. The assembled sheet is measured with a finger where Send is painted: Send and
// Cancel inside the box's clip and the viewport, elementFromPoint at Send's centre IS Send, a real click there posts
// the userTodoAnswer message and closes the sheet by the send, never by the backdrop. The answer's cap is the room the
// box has left, read from the box, and the box scrolls at every height (#ut-reply-prompt .picker-box), so the same is
// measured after the answer has grown and the window then shrinks (900 to 508 and 420: kbFit re-runs grow), at 420
// under the fold, at 490 with a todo that has no detail, and at 900.
//
// The browser legs (Chromium, Firefox, and WebKit when the box has them) open the page at the phone's width and drive
// the viewport's HEIGHT as the keyboard would (inside the shell the chat iframe is sized to the visible height, so its
// innerHeight is the keyboard's signal). The composition tap is its own test per engine, its outcome asserted first,
// so the deciding figure has a red of its own on a tree without the fix; the chip todo is also measured at 420, where
// the chat's column fits the fold's cap (the pane's does not: waiting-reply-sheet-browser.test.ts measures that
// backstop state). On the base tree at 508 the focus had scrolled the overflow-hidden box to the textarea, so the
// title, the ask and most of the detail sat above the clip with no way to scroll back; the first red differs by engine
// (Chromium and WebKit: the answer box a 14px sliver, and in WebKit the buttons below the clip too; Firefox: the rows
// kept and the buttons in reach), and the detail's computed overflow-y, visible there, is the red common to all three.
// The click that ends a drag of the grip is not a tap on the backdrop (the author's pass after the maintainer's round 1,
// composition-2): at 508 the box is at its cap, so a grip pull released past its bottom edge leaves the pointer over the
// backdrop, and Chromium and WebKit dispatch that click to the overlay, the common ancestor of the press and the
// release, which before the guard closed the sheet with the answer (Firefox retargets it to the textarea); now the sheet
// stands with its text in every engine, and a plain tap on the backdrop still dismisses. A dragged height is the person's
// PREFERENCE on the resize path (composition-3): pulled to 215px at 900, the keyboard opening clamps the box to the room,
// not to its content, and the keyboard closing returns it to 215px; before, the dragged height stood through the resize
// and Send lay below the frame.
// Where they skip, the served leg tests/test_reply_sheet_served.py runs the same composition against the served chat
// page in CI's browser step. Synthetic fixtures only: a placeholder sid, an invented path.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const STYLES_CSS = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");

// one top-level function of render.ts, whole, by name (render-todo-file-chip.test.ts liftRender)
function lift(name: string): string {
  const at = RENDER.indexOf("\nfunction " + name + "(");
  const end = RENDER.indexOf("\n}\n", at);
  assert.ok(at > 0 && end > at, "anchor not found: render.ts's " + name + " moved; re-anchor");
  return RENDER.slice(at, end + 3);
}
// the sheet's builder and the two chip builders, as render.ts has them, bundled for the page with the modules they
// import and stand-ins for the rest of the scope they read
function sheetBundle(): string {
  const esbuild = requireCjs("esbuild");
  const entry = [
    'import { openPathLink } from "./path-links";',
    'import { urlChip, linkifyUrls } from "./url-links";',
    "declare const window: any;",
    "const el = (tag: string, cls?: string): HTMLElement => { const e = document.createElement(tag); if (cls) e.className = cls; return e; };",
    "const linkTodoLinePaths = (node: HTMLElement, _sid: string | null): void => { linkifyUrls(node); };",
    "const linkTodoDetailPaths = (node: HTMLElement, _sid: string | null): void => { linkifyUrls(node); };",
    "const linkifyPrRefs = (_node: HTMLElement, _repo: string | null): void => { /* not under test */ };",
    "const prRepoFor = (_sid: string): string | null => null;",
    "const vscodeApi = { postMessage: (m: unknown) => { (window.__posted = window.__posted || []).push(m); } };",
    lift("todoFileChip"), lift("todoLinkChip"), lift("showUserTodoReply"),
    "window.__openReply = showUserTodoReply;",
  ].join("\n");
  const r = esbuild.buildSync({
    stdin: { contents: entry, resolveDir: UI, loader: "ts", sourcefile: "reply-sheet-page.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}

// synthetic fixtures: the notes-api demo's question, a forty-line detail; the composition fixture's wrapped ask, file and
// address, its detail's first line carrying an address; a todo with no detail
const SID = "11111111-2222-3333-4444-555555555555";
const TEXT = "Which layout should the quarterly report use?";
const DETAIL = Array.from({ length: 40 }, (_, i) => `Option ${i + 1}: the summary section leads and the tables follow, with the notes folded under each table.`).join("\n")
  + "\nreport-layout-" + "x".repeat(90);   // an unbreakable token wider than the sheet: without overflow-wrap it made the detail a sideways scroller
const LONG_TEXT = "Which layout should the quarterly report use for the regional tables, the summary section and the appendix, given that the notes under each table now run to several lines and the reviewers asked for the totals to lead every page rather than close it?";
const FILE = "/srv/notes-api/docs/quarterly-report-layout.md";
const LINK = "https://github.com/example-org/notes-api/pull/398";
const LINKED_DETAIL = "The earlier draft is at https://github.com/example-org/notes-api/pull/398 and the reviewers' notes follow.\n" + DETAIL;
type Todo = { id: string; text: string; detail?: string; file?: string; link?: string };
const TODOS: Todo[] = [
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
// the chat page: an empty transcript, the builder's bundle; the test opens the sheet through window.__openReply
const PAGE_HTML = (js: string) => `<!DOCTYPE html><html><head><meta charset=utf-8><link href=/dist/styles.css rel=stylesheet></head><body>
<div id="content"></div>
<script>${js}</script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Rect = { top: number; bottom: number; left: number; right: number };
type Sheet = {
  frameH: number; tight: boolean; alignItems: string; paddingTop: string;
  inputH: number; floorH: number; lineHeight: string; inputStyleH: string;
  detailScrollH: number; detailClientH: number; detailOverflowY: string; detailLineH: number; detailFontPx: number; detailScrolls: boolean;
  detailTextRight: number; detailRight: number; detailOverflowX: string; detailScrollW: number; detailOffsetW: number;
  actionsBottom: number; boxTop: number; boxBottom: number; boxScrollH: number; boxClientH: number; boxOverflowY: string;
  sendRect: Rect; cancelRect: Rect; hitAtSend: string; hitAtCancel: string; kinds: string[]; quoteChips: string[];
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
  const js = sheetBundle();
  const page = await browser.newPage({ viewport: { width: PHONE_W, height: KEYBOARD_UP } });
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await page.route("http://romp.test/**", (route: any) => {
    const u = new URL(route.request().url());
    if (u.pathname === "/chat") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE_HTML(js) });
    if (u.pathname === "/dist/styles.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: STYLES_CSS });
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto("http://romp.test/chat");
  const settle = () => page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
  // the keyboard: the viewport's height, which the page's window sees as its own resize
  const setHeight = async (h: number) => {
    await page.setViewportSize({ width: PHONE_W, height: h });
    await page.waitForFunction((hh: number) => window.innerHeight === hh, h, { timeout: 10000 });
    await settle();
  };
  const measure = (): Promise<Sheet | null> => page.evaluate(() => {
    const overlay = document.getElementById("ut-reply-prompt");
    if (!overlay) return null;
    const box = overlay.querySelector(".confirm-box") as HTMLElement;
    const input = overlay.querySelector(".ut-reply-input") as HTMLTextAreaElement;
    const detail = overlay.querySelector(".ut-detail") as HTMLElement | null;
    const quote = overlay.querySelector(".ut-reply-quote") as HTMLElement;
    const actions = overlay.querySelector(".confirm-actions") as HTMLElement;
    const [cancel, send] = Array.from(actions.querySelectorAll("button")) as HTMLElement[];
    const cs = (e: Element) => getComputedStyle(e);
    const rect = (e: Element) => { const r = e.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, left: r.left, right: r.right }; };
    const hit = (e: HTMLElement) => {
      const r = e.getBoundingClientRect(); const at = document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2);
      return at === e ? "target" : at === overlay ? "overlay" : at === box ? "box" : at ? ((at as HTMLElement).className || at.tagName).split(" ")[0] : "none";
    };
    // the three-row height in THIS engine: a probe of the same class, rows=3, outside the sheet and OUT OF FLOW (position
    // fixed, as in the served leg's driver: the chat page's body is a full-height flex column, and a probe in flow there
    // is a shrinkable flex item, the very squeeze under test); measured and removed
    const probe = document.createElement("textarea"); probe.className = "ut-reply-input"; probe.rows = 3;
    probe.style.position = "fixed"; probe.style.top = "0"; probe.style.left = "0"; probe.style.width = "300px"; probe.style.visibility = "hidden";
    document.body.appendChild(probe);
    const floorH = probe.clientHeight;
    probe.remove();
    return {
      frameH: window.innerHeight, tight: overlay.classList.contains("kb-tight"), alignItems: cs(overlay).alignItems, paddingTop: cs(overlay).paddingTop,
      inputH: input.clientHeight, floorH, lineHeight: cs(input).lineHeight, inputStyleH: input.style.height,
      detailScrollH: detail ? detail.scrollHeight : 0, detailClientH: detail ? detail.clientHeight : 0, detailOverflowY: detail ? cs(detail).overflowY : "",
      detailLineH: detail ? parseFloat(cs(detail).lineHeight) : 0, detailFontPx: detail ? parseFloat(cs(detail).fontSize) : 0,
      // the detail's sideways overflow: scrollWidth against offsetWidth (the border box; clientWidth is narrowed by a classic
      // scrollbar in WebKit headless while the text lays out to the border box); the widest text rect beside it for the
      // record only, since a trailing space hanging at a soft wrap ends a few pixels past the line box
      detailTextRight: detail ? ((): number => { const rg = document.createRange(); rg.selectNodeContents(detail); return Array.from(rg.getClientRects()).reduce((w, x) => Math.max(w, x.right), 0); })() : 0,
      detailRight: detail ? detail.getBoundingClientRect().right : 0, detailOverflowX: detail ? cs(detail).overflowX : "",
      detailScrollW: detail ? detail.scrollWidth : 0, detailOffsetW: detail ? detail.offsetWidth : 0,
      // the overflow declaration, live: a scroll container's scrollTop moves; with overflow visible it stays at 0
      detailScrolls: detail ? ((): boolean => { detail.scrollTop = 30; const moved = detail.scrollTop > 0; detail.scrollTop = 0; return moved; })() : false,
      actionsBottom: actions.getBoundingClientRect().bottom, boxTop: box.getBoundingClientRect().top, boxBottom: box.getBoundingClientRect().bottom,
      boxScrollH: box.scrollHeight, boxClientH: box.clientHeight, boxOverflowY: cs(box).overflowY,
      sendRect: rect(send), cancelRect: rect(cancel), hitAtSend: hit(send), hitAtCancel: hit(cancel),
      kinds: Array.from(box.children).map((c) => (["wt-file", "wt-link", "ut-file", "ut-link"].find((k) => c.classList.contains(k)) || (c.className || c.tagName).split(" ")[0])),
      quoteChips: Array.from(quote.querySelectorAll(".ut-file, .ut-link")).map((c) => (c.classList.contains("ut-file") ? "ut-file" : "ut-link")),
    };
  });
  const probeShort = (): Promise<Short> => page.evaluate(() => {
    const overlay = document.getElementById("ut-reply-prompt")!;
    const box = overlay.querySelector(".confirm-box") as HTMLElement;
    const detail = overlay.querySelector(".ut-detail") as HTMLElement;
    const send = overlay.querySelectorAll(".confirm-actions button")[1] as HTMLElement;
    const hit = (e: HTMLElement) => {
      const r = e.getBoundingClientRect(); const at = document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2);
      return at === e ? "target" : at === overlay ? "overlay" : at === box ? "box" : at ? ((at as HTMLElement).className || at.tagName).split(" ")[0] : "none";
    };
    const inBox = (e: Element) => { const r = e.getBoundingClientRect(), b = box.getBoundingClientRect(); return r.top >= b.top - 0.5 && r.bottom <= b.bottom + 0.5; };
    box.scrollTop = 0; detail.scrollTop = 0;
    detail.scrollIntoView({ block: "nearest" });   // the box scrolls the detail into view, as a finger would
    const a = detail.querySelector("a") as HTMLElement | null;
    // the address wraps at the phone's width, so the finger goes to the centre of its FIRST line fragment, not of the
    // union rect (whose centre can fall between the fragments)
    const first = a ? (a.getClientRects()[0] || a.getBoundingClientRect()) : null;
    const atLink = first ? document.elementFromPoint((first.left + first.right) / 2, (first.top + first.bottom) / 2) : null;
    const linkHit = !a ? "no-link" : atLink === a ? "target" : atLink ? ((atLink as HTMLElement).className || atLink.tagName).split(" ")[0] : "none";
    detail.scrollTop = 30; const detailScrolls = detail.scrollTop > 0; detail.scrollTop = 0;
    box.scrollTop = box.scrollHeight;   // to the bottom, where the buttons are
    const out = { frameH: window.innerHeight, tight: overlay.classList.contains("kb-tight"), detailH: detail.clientHeight, detailLineH: parseFloat(getComputedStyle(detail).lineHeight),
      detailScrolls, linkHit, boxScrollH: box.scrollHeight, boxClientH: box.clientHeight, boxScrollTop: box.scrollTop, sendHitAtBottom: hit(send), sendInBoxAtBottom: inBox(send) };
    box.scrollTop = 0;
    return out;
  });
  const openReply = async (t: Todo) => {
    await page.evaluate(([sid, todo]: [string, Todo]) => { (window as any).__posted = []; (window as any).__openReply(sid, todo.id, todo.text, todo.detail || "", todo.file || "", todo.link || ""); }, [SID, t] as [string, Todo]);
    await page.locator("#ut-reply-prompt .ut-reply-input").waitFor({ timeout: 10000 });
    await settle();
  };
  const cancelReply = async () => {
    await page.locator("#ut-reply-prompt .confirm-actions button").first().click();
    await page.waitForFunction(() => !document.getElementById("ut-reply-prompt"), null, { timeout: 10000 });
  };
  const fill = async (text: string) => { await page.locator("#ut-reply-prompt .ut-reply-input").fill(text); await settle(); };
  const waitTight = (on: boolean) => page.waitForFunction((want: boolean) => document.getElementById("ut-reply-prompt")?.classList.contains("kb-tight") === want, on, { timeout: 10000 });
  // the tap: a real click at Send's painted centre, then what the sheet did: is the overlay still up, what was posted
  const tapSend = async () => {
    const m = (await measure())!;
    const c = centre(m.sendRect);
    const inFrame = c.y >= 0 && c.y <= m.frameH && c.x >= 0 && c.x <= PHONE_W;
    if (inFrame) await page.mouse.click(c.x, c.y);
    await settle();
    const after: { overlayUp: boolean; posted: Array<{ type: string; id: string; todoId: string; text: string }> } = await page.evaluate(() => ({
      overlayUp: !!document.getElementById("ut-reply-prompt"),
      posted: ((window as any).__posted || []).filter((p: any) => p && p.type === "userTodoAnswer").map((p: any) => ({ type: p.type, id: p.id, todoId: p.todoId, text: String(p.text).slice(0, 40) })),
    }));
    return { before: m, tapAt: c, inFrame, ...after };
  };
  // the person pulls the box taller: a native drag of the resize grip (the textarea's bottom-right corner, inside the
  // border; resize: vertical), and where the headless engine's grip does not move (WebKit, in the round-1 refuters'
  // runs) the inline height written as the grip writes it; the road taken is reported with the result
  const dragTaller = async () => {
    const before = (await measure())!;
    const r = await page.evaluate(() => { const b = document.querySelector("#ut-reply-prompt .ut-reply-input")!.getBoundingClientRect(); return { right: b.right, bottom: b.bottom }; });
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
      await page.evaluate(() => { (document.querySelector("#ut-reply-prompt .ut-reply-input") as HTMLElement).style.height = "150px"; });
      await settle();
      m = (await measure())!;
    }
    return { road, dragged: m };
  };
  // the click that ends a drag of the grip (the author's pass after the maintainer's round 1, composition-2): the grip pulled
  // past the box's bottom edge and released over the backdrop. At 508 the box is at its cap, so it cannot grow with the answer
  // box and the pointer leaves it; Chromium and WebKit dispatch the click to the overlay, the common ancestor of the press and
  // the release, Firefox to the textarea. Every click on the document is recorded in the capture phase, so the record
  // names the click's target per engine. Where the headless grip does not move, the inline height is written under the press,
  // as the grip writes it, before the release; the road is reported
  const dragRelease = async (past = 30) => {
    await page.evaluate(() => {
      const w = window as any;
      w.__clicks = [];
      if (!w.__clickRec) { w.__clickRec = true; w.document.addEventListener("click", (e: any) => { w.__clicks.push(String(e.target.id || e.target.className || e.target.tagName).split(" ")[0]); }, true); }
    });
    const before = (await measure())!;
    const r = await page.evaluate(() => {
      const d = document;
      const i = d.querySelector("#ut-reply-prompt .ut-reply-input")!.getBoundingClientRect(); const b = d.querySelector("#ut-reply-prompt .confirm-box")!.getBoundingClientRect();
      return { right: i.right, bottom: i.bottom, boxTop: b.top, boxBottom: b.bottom };
    });
    await page.mouse.move(r.right - 5, r.bottom - 5);
    await page.mouse.down();
    await page.mouse.move(r.right - 5, r.boxBottom + past - 12, { steps: 8 });
    await page.mouse.move(r.right - 5, r.boxBottom + past, { steps: 4 });
    const mid = (await measure())!;
    let road = "native grip";
    if (mid.inputStyleH === before.inputStyleH) {
      road = "scripted (the headless grip did not move): the inline height written under the press, as the grip writes it";
      await page.evaluate((h: number) => { (document.querySelector("#ut-reply-prompt .ut-reply-input") as HTMLElement).style.height = h + "px"; }, before.inputH + 60);
      await settle();
    }
    await page.mouse.up();
    await settle();
    await page.waitForTimeout(300);
    const after: { overlayUp: boolean; value: string | null; clicks: string[]; posted: number } = await page.evaluate(() => {
      const w = window as any; const d = document;
      const i = d.querySelector("#ut-reply-prompt .ut-reply-input") as HTMLTextAreaElement | null;
      return { overlayUp: !!d.getElementById("ut-reply-prompt"), value: i ? i.value : null, clicks: w.__clicks as string[], posted: (w.__posted || []).filter((p: any) => p && p.type === "userTodoAnswer").length };
    });
    return { road, endY: r.boxBottom + past, boxBottom: r.boxBottom, inputStyleHMid: mid.inputStyleH, ...after };
  };
  // a plain tap on the backdrop, above the box
  const tapBackdrop = async () => {
    const top: number = await page.evaluate(() => document.querySelector("#ut-reply-prompt .confirm-box")!.getBoundingClientRect().top);
    const at = { x: PHONE_W / 2, y: Math.max(4, Math.round(top / 2)) };
    await page.mouse.click(at.x, at.y);
    await settle();
    await page.waitForTimeout(200);
    const overlayUp: boolean = await page.evaluate(() => !!document.getElementById("ut-reply-prompt"));
    return { at, overlayUp };
  };
  return { page, setHeight, settle, measure, probeShort, openReply, cancelReply, fill, tapSend, dragTaller, dragRelease, tapBackdrop, waitTight, errors };
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

const sendInsideBox = (m: Sheet) => m.sendRect.top >= m.boxTop - 0.5 && m.sendRect.bottom <= m.boxBottom + 0.5;
const cancelInsideBox = (m: Sheet) => m.cancelRect.top >= m.boxTop - 0.5 && m.cancelRect.bottom <= m.boxBottom + 0.5;
const boxInsideFrame = (m: Sheet) => m.boxTop >= -0.5 && m.boxBottom <= m.frameH + 0.5;
const where = (m: Sheet) => `Send ${rectOf(m.sendRect)}, Cancel ${rectOf(m.cancelRect)}, box ${m.boxTop.toFixed(1)}..${m.boxBottom.toFixed(1)} (${m.boxClientH} of ${m.boxScrollH}px, overflow-y ${m.boxOverflowY}), viewport ${m.frameH}px, input ${m.inputH}px (floor ${m.floorH}), detail ${m.detailClientH} of ${m.detailScrollH}px`;
const reachable = (m: Sheet) => m.actionsBottom <= m.frameH + 0.5 || (m.boxOverflowY === "auto" && m.boxScrollH > m.boxClientH + 1);
function assertFits(m: Sheet, what: string) {
  assert.ok(boxInsideFrame(m), `${what}: the box is inside the viewport (${where(m)})`);
  assert.ok(sendInsideBox(m) && cancelInsideBox(m), `${what}: Cancel and Send are inside the box's clip (${where(m)})`);
  assert.ok(m.boxScrollH <= m.boxClientH + 1, `${what}: the box's content fits its cap, so nothing is a scroll away (${where(m)})`);
  assert.equal(m.hitAtSend, "target", `${what}: a finger at Send's painted centre reaches Send (${where(m)})`);
  assert.equal(m.hitAtCancel, "target", `${what}: a finger at Cancel's painted centre reaches Cancel (${where(m)})`);
}

for (const name of ["chromium", "firefox", "webkit"]) {
  test(`in ${name}: the chat's Reply sheet holds three rows with the keyboard up, the detail scrolls within its cap, the buttons stay in view; the fold follows the window's height; a tap where Send is painted sends`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension, and the browser legs need it; the served leg tests/test_reply_sheet_served.py runs this composition in CI's browser step"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box, and this leg needs it; the served leg tests/test_reply_sheet_served.py is the guard where this skips (CI's browser step runs it in chromium): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { page, setHeight, settle, measure, probeShort, openReply, cancelReply, fill, tapSend, dragTaller, dragRelease, tapBackdrop, waitTight, errors } = await boot(browser);
      await openReply(TODOS[0]);
      // ── 508px: the keyboard up on a phone, above the fold's threshold: the squeeze fix alone
      let m = (await measure())!;
      assert.ok(m, "the Reply sheet is up");
      assert.equal(m.frameH, KEYBOARD_UP);
      assert.equal(m.tight, false, "508px is not a short window: no fold, so what follows is the squeeze fix on its own");
      assert.deepEqual(m.kinds, ["confirm-title", "confirm-detail", "ut-detail", "ut-reply-input", "confirm-actions"], "the builder's tree: title, the quoted line, the detail, the answer box, the buttons");
      assert.ok(m.floorH > 30, `the probe laid out three rows (${m.floorH}px; line-height ${m.lineHeight})`);
      assert.ok(m.inputH >= m.floorH - 1, `the answer box holds three rows: ${m.inputH}px against the ${m.floorH}px three-row probe (on the base tree it was a 14px sliver in Chromium and WebKit, the textarea taking the whole deficit; Firefox kept the rows there, so the detail's overflow-y assertion below is its first red, and the base tree's red in all three engines)`);
      assert.equal(m.detailOverflowY, "auto", "the detail scrolls within itself (the base tree computes visible in Chromium, Firefox and WebKit alike: the red common to the three engines, reached first in Firefox, where the textarea kept its rows and the buttons stayed in reach; there the focus had scrolled the overflow-hidden box to the textarea, so the title, the ask and most of the detail sat above the clip with no way to scroll back, in every engine)");
      assert.ok(m.detailScrolls, "the overflow declaration is LIVE: the detail's scrollTop moves (with overflow visible it stays at 0, and the detail's text paints over the answer box); the rule pin reads the sheet with comments stripped, this reads the engine");
      assert.ok(m.detailScrollH > m.detailClientH + 8, `the forty-line detail overflows its cap and is a scroll away (${m.detailClientH} of ${m.detailScrollH}px)`);
      assert.ok(m.detailScrollW <= m.detailOffsetW, `no sideways scroller: the unbreakable token in the detail wraps inside the box (overflow-wrap: anywhere), so the detail's content is no wider than its border box (scrollWidth ${m.detailScrollW} against offsetWidth ${m.detailOffsetW}; the widest text rect ends at ${m.detailTextRight.toFixed(1)} against the detail's ${m.detailRight.toFixed(1)}px, a figure a trailing space hanging at a soft wrap pushes a few pixels past the edge, so it is not the bar); without the wrap the token ran hundreds of pixels past it and a scroll container's overflow-x, computing to auto, scrolled sideways`);
      assert.equal(m.detailOverflowX, "hidden", "overflow-x: hidden, #pinned-notes's companion declaration, so a token the wrap cannot break is clipped, never a sideways scroll");
      assert.ok(m.detailClientH > 20, `the detail still shows some lines (${m.detailClientH}px)`);
      assert.ok(m.actionsBottom > 0 && m.actionsBottom <= m.frameH + 0.5, `Cancel and Send are inside the viewport (bottom edge ${m.actionsBottom.toFixed(1)} of ${m.frameH}px)`);
      assert.ok(m.boxBottom <= m.frameH + 0.5, `the whole box is inside the viewport (${m.boxBottom.toFixed(1)} of ${m.frameH}px)`);
      assert.equal(m.boxOverflowY, "auto", "the box scrolls at this height too, not only under the fold: the every-height backstop (#ut-reply-prompt .picker-box)");
      // ── 420px: a short window: the builder's kbFit, on the window's own resize
      await setHeight(KEYBOARD_TIGHT);
      await waitTight(true);
      m = (await measure())!;
      assert.equal(m.tight, true, "under 480px the sheet wears kb-tight");
      assert.equal(m.alignItems, "flex-start", "folded, the sheet sits at the top rather than centering into the keyboard");
      assert.equal(m.paddingTop, "12px", "under the picker's 12px frame");
      assert.ok(m.inputH >= m.floorH - 1, `folded, the answer box still holds three rows (${m.inputH} against ${m.floorH}px)`);
      assert.ok(m.detailScrollH > m.detailClientH + 8, `folded, the detail still scrolls (${m.detailClientH} of ${m.detailScrollH}px)`);
      assert.ok(reachable(m), `folded, the buttons are reachable (bottom edge ${m.actionsBottom.toFixed(1)} of ${m.frameH}px; box ${m.boxClientH} of ${m.boxScrollH}px, overflow-y ${m.boxOverflowY})`);
      assert.ok(m.boxClientH <= KEYBOARD_TIGHT - 24 + 1, `the box is capped at the visible height less the 12px frame (${m.boxClientH}px)`);
      // ── typing: the builder's grow handler, on the real textarea, capped at the room the box has left
      const before = m.inputH;
      await fill(ANSWER(12));
      m = (await measure())!;
      assert.ok(m.inputH > before + 20, `twelve lines grow the box (${before} → ${m.inputH}px)`);
      assertFits(m, "folded, the answer grown");
      assert.ok(m.detailClientH >= floorOf(m.detailLineH), `folded, the answer grown: the detail keeps its floor of two lines (${m.detailClientH}px against a ${m.detailLineH}px line); the deficit state, which round 1 never measured`);
      await fill("");
      m = (await measure())!;
      assert.ok(Math.abs(m.inputH - before) <= 2, `cleared, the box is back at the floor (${m.inputH} vs ${before}px)`);
      // ── 900px: the keyboard down
      await setHeight(TALL);
      await waitTight(false);
      m = (await measure())!;
      assert.equal(m.tight, false, "the room back, the fold comes off");
      assert.notEqual(m.alignItems, "flex-start", "the sheet centers again (.confirm-overlay)");
      assert.ok(m.inputH >= m.floorH - 1, `tall, the answer box holds three rows (${m.inputH} against ${m.floorH}px)`);
      assert.ok(m.actionsBottom <= m.frameH + 0.5, "the buttons are inside the viewport");
      // the cap at rest, where nothing squeezes: 12em of the detail's own font (about eight and a half lines), the whole of it
      // executed rather than a spelling; the keyboard-up heights above are the shrink and the floor, not this cap
      assert.ok(Math.abs(m.detailClientH - 12 * m.detailFontPx) <= 1.5, `tall, the forty-line detail sits at its cap: ${m.detailClientH}px against 12em of its ${m.detailFontPx}px font (${(12 * m.detailFontPx).toFixed(1)}px)`);
      // ── the answer grown TALL, then the keyboard: the window shrinks under an answer already grown, and the resize re-fits it
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
      await page.locator("#ut-reply-prompt .ut-reply-input").focus();
      await page.keyboard.type("a");
      await settle();
      m = (await measure())!;
      assert.equal(m.inputStyleH, d.dragged.inputStyleH, `one keystroke after the drag (${d.road}): the inline height the person set stands, grow stood down (before the guard it snapped back to the floor: ${m.inputH}px)`);
      assert.ok(m.inputH >= d.dragged.inputH - 1, `and the box keeps the dragged height (${m.inputH} against ${d.dragged.inputH}px)`);
      await setHeight(KEYBOARD_UP);
      await waitTight(false);
      await cancelReply();
      // ── THE COMPOSITION, at 390 by 508 with the keyboard up: the ask wrapped to several lines with both chips inside it, the
      // forty-line detail, the answer grown to the cap: the state in which the round-1 tree laid Send out below the box's clip
      await openReply(TODOS[1]);
      m = (await measure())!;
      assert.deepEqual(m.kinds, ["confirm-title", "confirm-detail", "ut-detail", "ut-reply-input", "confirm-actions"], "the chat's sheet: the chips are inside the quoted line, not children of the box (render.ts showUserTodoReply; the pane's builder appends them as flex children)");
      assert.deepEqual(m.quoteChips, ["ut-file", "ut-link"], "both chips trail the quoted line, the file's first");
      assert.equal(m.tight, false, "508px: no fold");
      assert.ok(m.inputH >= m.floorH - 1, `with the chips and the wrapped ask the answer box holds three rows (${m.inputH} against ${m.floorH}px)`);
      // ── short windows with this sheet up, the floors alone past the box's cap: 300px (a short portrait phone under the
      // keyboard) and 230px (a landscape phone). The detail keeps two lines, the box scrolls to the rest
      await setHeight(300);
      await waitTight(true);
      assertShort(await probeShort(), "300px, the chip todo");
      await setHeight(230);
      assertShort(await probeShort(), "230px, the chip todo");
      // ── 420px with the chip todo (the fold on): the chat's chips sit inside the quoted line, so its column FITS the fold's cap
      // at the floors and after fourteen lines (the fitted state; the pane's two chip rows put its floors past the cap, the
      // backstop state waiting-reply-sheet-browser.test.ts measures). Measured, so the body's account of this window is read
      // from the engine in both panes
      await setHeight(KEYBOARD_TIGHT);
      m = (await measure())!;
      assert.equal(m.tight, true, "420px with the chip todo: under the fold");
      assert.ok(m.detailClientH >= floorOf(m.detailLineH), `420px, the chip todo, at open: the detail keeps its floor of two lines (${m.detailClientH}px against a ${m.detailLineH}px line)`);
      assertFits(m, "420px, the chip todo, at open");
      await fill(ANSWER(14));
      m = (await measure())!;
      assert.ok(m.inputH >= m.floorH - 1, `420px, the chip todo, fourteen lines: three rows at least (${m.inputH} against ${m.floorH}px)`);
      assert.ok(m.detailClientH >= floorOf(m.detailLineH), `420px, the chip todo, fourteen lines: the detail keeps its floor (${m.detailClientH}px against a ${m.detailLineH}px line)`);
      assertFits(m, "420px, the chip todo, fourteen lines");
      await fill("");
      await setHeight(KEYBOARD_UP);
      await waitTight(false);
      // ── the dragged height is a PREFERENCE clamped to the room (the author's pass after the maintainer's round 1, composition-3):
      // the box pulled to 215px at 900 (the inline height written as the grip leaves it, so the preference is the same in every
      // engine), the keyboard then opens (508): the box is clamped to the room the sheet has, not reset to the content's height,
      // Send inside the clip and under a finger; the keyboard closes (900): the box returns to the 215px the person set, not stuck
      // at the clamp. Before, the dragged height stood through the resize, the box overflowed its cap and Send lay below the frame
      await setHeight(TALL);
      await waitTight(false);
      await page.evaluate(() => { (document.querySelector("#ut-reply-prompt .ut-reply-input") as HTMLElement).style.height = "215px"; });
      await settle();
      m = (await measure())!;
      assert.equal(m.inputStyleH, "215px", `900px: the dragged 215px stands, the room holds it (${where(m)})`);
      const draggedTall = m.inputH;
      await setHeight(KEYBOARD_UP);
      m = (await measure())!;
      assert.ok(m.inputH < draggedTall - 20, `508px after the drag: the box is clamped to the room (${m.inputH}px against the ${draggedTall}px the drag laid out); before the clamp the dragged height stood through the resize and Send lay below the frame (${where(m)})`);
      assert.ok(m.inputH > m.floorH, `508px after the drag: clamped to the room, not reset to the content's height (${m.inputH}px against the ${m.floorH}px floor of an empty box) (${where(m)})`);
      assertFits(m, "508px after the drag, clamped to the room");
      await setHeight(TALL);
      await waitTight(false);
      m = (await measure())!;
      assert.equal(m.inputStyleH, "215px", `900px again: the box returns to the height the person set, not stuck at the clamp (${where(m)})`);
      assert.ok(m.inputH >= draggedTall - 1, `and lays out at it (${m.inputH} against ${draggedTall}px)`);
      await setHeight(KEYBOARD_UP);
      await waitTight(false);
      // ── the click that ends a drag of the grip is not a tap on the backdrop (the author's pass after the maintainer's round 1,
      // composition-2). At 508 the box is at its cap, so a grip pull released past its bottom edge leaves the pointer over the
      // backdrop; Chromium and WebKit dispatch that click to the overlay, the common ancestor of the press and the release, and
      // before the guard it closed the sheet with the answer (Firefox retargets the click to the textarea). The sheet stands with
      // its text in every engine, and a plain tap on the backdrop still dismisses (what a dismiss does is the filed discard item's)
      await fill(ANSWER(3));
      const rel = await dragRelease();
      t.diagnostic(`${name}: the drag's release: ${rel.road}; released at y ${rel.endY.toFixed(1)}, past the box's bottom ${rel.boxBottom.toFixed(1)}; the clicks' targets ${JSON.stringify(rel.clicks)}`);
      assert.equal(rel.overlayUp, true, `the click that ends a grip drag released over the backdrop (${rel.road}; the clicks' targets ${JSON.stringify(rel.clicks)}) is not a dismissal: the sheet stands (before the guard Chromium and WebKit closed it with the answer; Firefox retargets the click to the textarea)`);
      assert.equal(rel.value, ANSWER(3), "and the answer is intact");
      assert.equal(rel.posted, 0, "the release posted nothing");
      const tapped = await tapBackdrop();
      assert.equal(tapped.overlayUp, false, `a plain tap on the backdrop (at ${tapped.at.x}, ${tapped.at.y}) still dismisses; what a dismiss does with the text is the filed discard item's, untouched here`);
      // ── the onset of the old clip band, 490px, a todo with no detail and a fourteen-line answer
      await setHeight(ONSET);
      await openReply(TODOS[2]);
      m = (await measure())!;
      assert.deepEqual(m.kinds, ["confirm-title", "confirm-detail", "ut-reply-input", "confirm-actions"], "no detail: the sheet's smallest tree");
      await fill(ANSWER(14));
      m = (await measure())!;
      assert.ok(m.inputH > m.floorH + 20, `490px, no detail: fourteen lines grow the box (${m.inputH} against ${m.floorH}px)`);
      assertFits(m, "490px, no detail, the answer grown");
      await cancelReply();
      assert.deepEqual(errors, [], "no script error on the page");
    } finally { await browser.close(); }
  });

  // THE COMPOSITION, as its own test so the deciding figure has a red of its own: at 390 by 508 with the keyboard up, the
  // ask wrapped to several lines with both chips inside it, the forty-line detail, the answer grown to the cap, a real click
  // where Send is painted. The tap's outcome is asserted FIRST: on the round-1 tree (and the base) the answer box laid Send
  // below the box's clip, so the finger found the backdrop and the sheet closed with nothing posted, and that is the
  // assertion that goes red there, not a geometry read before it. The geometry follows, as the explanation of the outcome
  test(`in ${name}: THE COMPOSITION at 390 by 508 with the keyboard up: a tap where Send is painted sends the answer, and the sheet closes by the send, never by the backdrop`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension, and the browser legs need it; the served leg tests/test_reply_sheet_served.py runs this composition in CI's browser step"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box, and this leg needs it; the served leg tests/test_reply_sheet_served.py is the guard where this skips (CI's browser step runs it in chromium): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { measure, openReply, fill, tapSend, errors } = await boot(browser);
      await openReply(TODOS[1]);
      const open = (await measure())!;
      await fill(ANSWER(14));
      const tap = await tapSend();
      const rec = JSON.stringify({ tapAt: tap.tapAt, inFrame: tap.inFrame, hitAtSend: tap.before.hitAtSend, sendRect: tap.before.sendRect, box: [tap.before.boxTop, tap.before.boxBottom, tap.before.boxClientH, tap.before.boxScrollH, tap.before.boxOverflowY], inputH: tap.before.inputH, detailH: tap.before.detailClientH, detailLineH: tap.before.detailLineH, after: { overlayUp: tap.overlayUp, posted: tap.posted } });
      assert.deepEqual(tap.posted.map((p) => [p.type, p.id, p.todoId, p.text.split("\n")[0]]), [["userTodoAnswer", SID, "t2", "line 1"]], `composition: the tap SENT the answer (one userTodoAnswer posted); on the round-1 tree the finger found the backdrop in every engine and nothing was posted (${rec})`);
      assert.equal(tap.overlayUp, false, `composition: the sheet closed by the send itself (${rec})`);
      assert.ok(tap.inFrame, `composition: the tap point is inside the viewport (${rec})`);
      assert.equal(tap.before.hitAtSend, "target", `composition: a finger at Send's painted centre reaches Send, not the backdrop (${rec})`);
      assert.ok(sendInsideBox(tap.before) && cancelInsideBox(tap.before), `composition: Cancel and Send are inside the box's clip (${where(tap.before)}); on the round-1 tree the answer box grown to 40% of the window laid them out below it`);
      assert.ok(boxInsideFrame(tap.before), `composition: the box is inside the viewport (${where(tap.before)})`);
      assert.ok(tap.before.detailClientH >= floorOf(tap.before.detailLineH), `composition: with the answer grown to the cap the detail keeps its floor of two lines (${tap.before.detailClientH}px against a ${tap.before.detailLineH}px line); on the round-1 tree it resolved to 0px here (${rec})`);
      assert.deepEqual(open.kinds, ["confirm-title", "confirm-detail", "ut-detail", "ut-reply-input", "confirm-actions"], "the chat's sheet: the chips are inside the quoted line, not children of the box (render.ts showUserTodoReply; the pane's builder appends them as flex children)");
      assert.deepEqual(open.quoteChips, ["ut-file", "ut-link"], "both chips trail the quoted line, the file's first");
      assert.equal(open.tight, false, "508px: no fold, so this is the room cap and the every-height scroll on their own");
      assert.deepEqual(errors, [], "no script error on the page");
    } finally { await browser.close(); }
  });
}
