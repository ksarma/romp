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
// figures are in the review record). That tap is its own test per engine, its outcome asserted first, so the deciding
// figure has a red of its own on a tree without the fix. The grow handler now caps the answer at the room the box has
// left, read from the box, and the box scrolls at every height (styles.css #ut-reply-prompt .picker-box), so the same
// is measured after the answer has grown and the window then shrinks (900 to 508 and to 420: kbFit re-runs grow on
// the resize), at 420 under the fold, at 490 (the onset of the band where the shared box rule alone left the clip)
// with a todo that has no detail and a fourteen-line answer, and at 900. At 420 with the chip todo the pane's two chip
// rows put the floors alone a few pixels past the fold's cap: the box scrolls the difference, and the actions row, kept in
// view at the box's bottom (styles.css #ut-reply-prompt .confirm-actions; the maintainer's round 2 ruling, B-i), holds
// Cancel and Send inside the clip at open and with the answer typed; the chat's column fits there
// (render-reply-sheet-browser.test.ts). Before the kept row Send's bottom edge lay 2 to 3px past the clip in that state,
// and with a 300-character ask, or at 320 wide, a finger at its centre closed the sheet with the answer: THE WORST CASE is
// its own test per engine (both widths, 230 to 508 with the keyboard up and in the phone's order, four asks at the cap,
// and after a grip drag, Send clicked at its centre in every cell). A click whose press began
// inside the sheet is not a backdrop tap (the author's pass after the maintainer's round 1, composition-2, and the
// reviewer's ruling on the selection): at 508 the box is at its cap, so a grip pull released past its bottom edge, or a
// text selection dragged out of the box, leaves the pointer over the backdrop, and Chromium and WebKit dispatch that
// click to the overlay, the common ancestor of the press and the release, which before the guard closed the sheet with
// the answer (Firefox retargets it to the textarea); now a backdrop tap is press and release both on the backdrop, the
// sheet stands with its text after either gesture in every engine, and a plain tap on the backdrop still dismisses. The reverse
// road is its own test per engine (the maintainer's round 2, ui-1): a press on the backdrop released on the answer box or the
// title reached the overlay as its click in all three engines and closed the sheet with the answer, and in Chromium so did a
// finger pressed just outside the box's edge and lifted inside it (a touch pointer is captured to the node it pressed, driven
// here through the DevTools protocol's touch input; touch in Firefox, WebKit and iOS is a stated residual); the sheet now
// stands through each, and a plain tap on the backdrop still dismisses. A dragged height is the person's PREFERENCE on the resize
// path (composition-3): pulled to 215px at 900, the keyboard opening clamps the box to the room, not to its content, and
// the keyboard closing returns it to 215px; before, the dragged height stood through the resize and Send lay below the
// frame.
//
// THE DETAIL'S CAP AT REST (the maintainer's ruling at the merge with main): with the keyboard down the cap is the larger
// of 12em and 34.8% of the window's height, so a tall window shows more of a long detail; with the keyboard up it
// is 12em, as at the head, and the flex shrink governs. Its own test per engine measures the viewport term at rest at
// the pane heights a phone gives (the maintainer's rulings on the cap pass and on the share: Safari's 620, 633 and 709;
// the installed app's 732) and at 900 and 1080, 12em at rest at 300 (the computed max-height: the room sets the
// rendered height there), 12em under the keyboard at 508 with the sheet opened at rest and the keyboard then raised and
// lowered under it, the tightest sheet (both chip rows) at its cap under its room at the app's 732 and at 900 and fitting
// with its detail under the cap in Safari's panes, and the recorded 8-line detail on both sides of the stated boundary (in
// full at 720, 732 and 900; not in full one pixel under each engine's own boundary and in Safari's panes, where it shows
// the cap and scrolls the rest). And a stated residual, pinned as it is: under Android Chrome's resizes-content the
// keyboard shrinks the shell page's layout viewport, restCap sees no keyboard, and at 508 the cap is the at-rest term
// (177px) with the room setting the detail's height.
//
// The browser legs (Chromium, Firefox, and WebKit when the box has them) load the kernel's /waiting page as it is
// served (styles.css, then the pane's sheet) with the worktree's waiting.ts bundle in a 390px-wide frame, the
// phone's width, and drive the frame's HEIGHT as the keyboard would: inside the shell the pane iframe is sized to the
// visible height (--app-h), so the frame's innerHeight IS the fold's signal and a shorter frame is the keyboard up. The
// detail's cap reads the keyboard where the shell does (restCap; kernel.py kbOpen): the shell's visual viewport shorter
// than its layout viewport. So with the keyboard up the leg also stubs the shell page's visualViewport.height to the
// frame's height, as the app's shell sizes the pane to it, and removes the stub at rest; every window under 900 is the
// keyboard up unless a step says it is at rest.
// Three todos are fed: one with a short ask and a forty-line detail (the configuration that pins the detail's cap), one
// with a near-300-character ask, a file chip, a link chip and the detail (the composition fixture: without the chips
// and the wrapped ask the box never clipped at 508), and one with no detail. On the base tree at 508 the focus had
// scrolled the overflow-hidden box to the textarea, so the title, the ask and most of the detail sat above the clip
// with no way to scroll back; the first red differs by engine (Chromium and WebKit: the answer box a 14px sliver, and in
// WebKit the buttons below the clip too; Firefox: the rows kept and the buttons in reach), and the detail's computed
// overflow-y, visible there, is the red common to all three. Where the legs skip (no playwright, no engine), the
// served leg tests/test_reply_sheet_served.py runs the same composition against the served pages in CI's
// "Browser-backed served-page tests (pytest)" step. These legs run in none of the job's browser-backed steps: the Test
// step runs them before the job installs its browser, so they skip there, and they are not on the roster of "Browser
// legs (node --test over ci-browser-legs.txt)".
// Synthetic fixtures only: the notes-api world, a placeholder sid, TESTHOST, an invented path.
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
// the recorded 8-line detail (the review record's extra10-4, 251px at this width): at the share of the detail's cap at rest
// it shows in full from a 720px pane (the stated boundary, styles.css #ut-reply-prompt .ut-detail.open), so at the
// installed app's 732 and at 900, and not in Safari's panes (620, 633, 709)
const DETAIL8 = Array.from({ length: 8 }, (_, i) => `Option ${i + 1}: the summary section leads and the tables follow, with the notes folded under each table.`).join("\n");
const LINKED_DETAIL = "The earlier draft is at https://github.com/example-org/notes-api/pull/398 and the reviewers' notes follow.\n" + DETAIL;
// THE WORST CASE (the maintainer's round 2 ruling, B-i): asks at the kernel's 300-character cap, each with both chips and the
// linked forty-one-line detail. The kernel strips only a todo's ends before that bound and the quoted line keeps its line
// breaks (white-space: pre-wrap), so the tallest legal ask is a list of short lines, about ten times the height of one wrapped
// paragraph; a 300-character token cannot break at a space; and a 300-character paragraph wraps to the most lines prose gives
const ASK300 = (LONG_TEXT + " The reviewers also want the appendix numbered by region and a short caption over every chart please.").slice(0, 300);
const ASK_LINES = ("Which?\n" + Array.from({ length: 60 }, (_, i) => "- " + (i + 1)).join("\n")).slice(0, 300).trim();
const ASK_TOKEN = "report-layout-" + "x".repeat(286);
const TODOS = [
  { id: "t1", text: TEXT, detail: DETAIL },
  { id: "t2", text: LONG_TEXT, detail: LINKED_DETAIL, file: FILE, link: LINK },
  { id: "t3", text: TEXT },
  { id: "t4", text: TEXT, detail: DETAIL8 },
  { id: "t5", text: ASK300, detail: LINKED_DETAIL, file: FILE, link: LINK },
  { id: "t6", text: ASK_LINES, detail: LINKED_DETAIL, file: FILE, link: LINK },
  { id: "t7", text: ASK_TOKEN, detail: LINKED_DETAIL, file: FILE, link: LINK },
];
const ANSWER = (n: number) => Array.from({ length: n }, (_, i) => `line ${i + 1}`).join("\n");
const PHONE_W = 390;
const KEYBOARD_UP = 508;   // above the fold's threshold: the squeeze fix alone
const KEYBOARD_TIGHT = 420;   // under it: the fold too
const ONSET = 490;   // the shared box rule's clip band began here (extra9-2's refuter): above the fold, under the old clip
const TALL = 900;
const SAFARI_16E = 620;   // a Safari pane at the phone's width: the 651px window of the iPhone 16e and 17e entries in Playwright's device registry, both toolbars shown, less the phone shell's 31px tab bar
const SAFARI_BARS = 633;   // the common Safari pane: the 664px window of the iPhone 12, 13 and 14 entries, both toolbars shown, less the tab bar
const SAFARI_TOP = 709;   // a Safari pane with the toolbars collapsed: a 740px window less the tab bar
const APP_PANE = 732;   // the installed app's pane on a 390x844 phone: its window is the screen less the status bar, less the app's 65px tab bar
const BOUNDARY = 720;   // the stated boundary: the recorded 8-line detail shows in full from a 720px pane (a 751px Safari window)
// one pixel under each engine's own boundary (720 in Chromium, 717 in WebKit, 718 in Firefox; measured in both panes)
const BELOW_BOUNDARY: Record<string, number> = { chromium: 719, firefox: 717, webkit: 716 };
const REST_TALL = 1080;   // a tall window at rest (the review record's extra10-4 measured the regression at this height)
const REST_SHORT = 300;   // a window at rest short enough that 12em is the larger term (34.8% of 300 is 104px)
const REST_SHARE = 0.348;   // the detail's cap at rest: max(12em, 34.8% of the window's height) (styles.css, where the share is derived)

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
// after it (the sheet's @import and font urls 404 here, so the text lays out in the fallback font, which gives the pane's
// chip sheet about a pixel more room than the served shell: the note above the detail's cap test says what that leaves to
// the served leg). The served shim's acquireVsCodeApi is a recorder
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
  detailScrollH: number; detailClientH: number; detailOverflowY: string; detailLineH: number; detailFontPx: number; detailMaxH: number; detailRectH: number; detailScrolls: boolean;
  detailTextRight: number; detailRight: number; detailOverflowX: string; detailScrollW: number; detailOffsetW: number;
  actionsBottom: number; boxTop: number; boxBottom: number; boxScrollH: number; boxClientH: number; boxOverflowY: string;
  sendRect: Rect; cancelRect: Rect; hitAtSend: string; hitAtCancel: string; kinds: string[];
};
// a short window, where the box itself must scroll: the detail's height against its floor (two of its lines), whether it
// scrolls within itself, whether the address on its first line is under a finger where the engine's own scroll left it
// (linkHit) and once the box is scrolled to bring its line to the top of the box's view (linkHitScrolled), and whether Send
// is inside the clip and under a finger once the box is scrolled to its bottom
type Short = {
  frameH: number; tight: boolean; detailH: number; detailLineH: number; detailScrolls: boolean; linkHit: string; linkHitScrolled: string;
  boxScrollH: number; boxClientH: number; boxScrollTop: number; sendHitAtBottom: string; sendInBoxAtBottom: boolean;
};
const floorOf = (lineH: number) => 2 * lineH - 1;   // two lines, less a pixel of rounding
const rectOf = (r: Rect) => `${r.top.toFixed(1)}..${r.bottom.toFixed(1)}`;
const centre = (r: Rect) => ({ x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2 });

async function boot(browser: any, browserName = "chromium") {
  const errors: string[] = [];
  const waitingJs = bundle("waiting.ts");
  const page = await browser.newPage({ viewport: { width: PHONE_W + 30, height: REST_TALL + 40 } });
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
  // the todos, fed as the kernel's frame feeds them; fed again before a worst-case cell, since a send drops the todo's row
  const feed = () => page.evaluate(([sid, name, todos]: [string, string, typeof TODOS]) => {
    const f = document.getElementById("f-waiting") as HTMLIFrameElement;
    const now = Math.floor(Date.now() / 1000);
    f.contentWindow!.postMessage({ type: "feed", now, userTodosOn: true, userTodoRows: [{ sid, name, color: { bg: "#123456", fg: "#ffffff" },
      todos: todos.map((t, i) => ({ id: t.id, text: t.text, createdT: now - 300 + i, ...(t.detail ? { detail: t.detail } : {}), ...(t.file ? { file: t.file } : {}), ...(t.link ? { link: t.link } : {}) })) }] }, "*");
  }, [SID, NAME, TODOS] as [string, string, typeof TODOS]);
  await feed();
  const W = page.frameLocator("#f-waiting");
  await W.locator(`.ut-reply[data-tid="t1"]`).waitFor({ timeout: 10000 });
  // two animation frames in the FRAME's window: a resize handler runs at the frame after the size changed, and grow's
  // writes need a layout before they are read
  const settle = () => page.evaluate(() => new Promise<void>((r) => { const w = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!; w.requestAnimationFrame(() => w.requestAnimationFrame(() => r())); }));
  // the keyboard's signal for the detail's cap (restCap, kernel.py kbOpen's test): the shell's visual viewport shorter than
  // its layout viewport. The app's shell sizes the pane iframe to its visual viewport, so with the keyboard up the shell
  // page's visualViewport.height is stubbed to the frame's height; at rest the stub is removed and the engine's getter
  // answers (the shell page's own height, its layout viewport's)
  const keyboard = (h: number | null) => page.evaluate((hh: number | null) => {
    const vv = window.visualViewport as any;
    if (hh === null) delete vv.height; else Object.defineProperty(vv, "height", { configurable: true, get: () => hh });
  }, h);
  // the keyboard: the frame's height, and the frame's window sees it as its own resize; a window under 900 is the keyboard
  // up unless the step says it is at rest. The shell's keyboard state is set before the resize, so kbFit reads it
  const setHeight = async (h: number, kb = h < TALL) => {
    await keyboard(kb ? h : null);
    await page.evaluate((hh: number) => { (document.getElementById("f-waiting") as HTMLIFrameElement).style.height = hh + "px"; }, h);
    await page.waitForFunction((hh: number) => (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.innerHeight === hh, h, { timeout: 10000 });
    await settle();
  };
  // the keyboard as Android Chrome 108 and later shows it, in a tab or installed (the stated residual at restCap): the
  // shell's meta asks for interactive-widget=resizes-content, which Chrome 108+ honours and iOS ignores, so the keyboard
  // shrinks the shell's LAYOUT viewport: the shell page itself is resized to h, its visual viewport is not stubbed (the two
  // agree), and the frame follows the shell's height as --app-h sizes it. restoreShell puts the shell page back at its own
  // height
  const setResizesContent = async (h: number) => {
    await keyboard(null);
    await page.setViewportSize({ width: PHONE_W + 30, height: h });
    await page.evaluate((hh: number) => { (document.getElementById("f-waiting") as HTMLIFrameElement).style.height = hh + "px"; }, h);
    await page.waitForFunction((hh: number) => window.innerHeight === hh && (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.innerHeight === hh, h, { timeout: 10000 });
    await settle();
  };
  const restoreShell = async () => { await page.setViewportSize({ width: PHONE_W + 30, height: REST_TALL + 40 }); await settle(); };
  await keyboard(KEYBOARD_UP);   // the frame opens at 508, the keyboard up
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
      detailMaxH: detail ? parseFloat(cs(detail).maxHeight) : 0,   // the cap the engine resolved: which arm of the max won
      // the detail's laid-out height, unrounded: at its cap it equals the resolved cap; under it, the room (the flex shrink) set it
      detailRectH: detail ? detail.getBoundingClientRect().height : 0,
      // the detail's sideways overflow: its scrollWidth (the content's width; a trailing space hanging at a soft wrap is left
      // out) against its offsetWidth, the border box (not clientWidth, which a classic vertical scrollbar in WebKit headless
      // narrows by its own width while the text still lays out to the border box). An unbreakable token that does not wrap
      // makes scrollWidth hundreds of pixels wider. The widest text rect is read beside it for the record only: at a soft
      // wrap the collapsed trailing space hangs a few pixels past the line box and Range.getClientRects reports it
      detailTextRight: detail ? ((): number => { const rg = d.createRange(); rg.selectNodeContents(detail); return Array.from(rg.getClientRects()).reduce((w, x) => Math.max(w, x.right), 0); })() : 0,
      detailRight: detail ? detail.getBoundingClientRect().right : 0, detailOverflowX: detail ? cs(detail).overflowX : "",
      detailScrollW: detail ? detail.scrollWidth : 0, detailOffsetW: detail ? detail.offsetWidth : 0,
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
    // the actions row, kept in view at the box's bottom (styles.css #ut-reply-prompt .confirm-actions), can cover what the engine
    // scrolled into view there (at 230 it covers this address in every engine, both panes: a finger aimed at it reaches Cancel or
    // Send); the person scrolls the box, and with the address's line brought to the top of the box's view it is under a finger
    // (the maintainer's round 2 ruling on B-i's cover: accepted where a covered link can be scrolled into the part the row leaves,
    // at 230 only; at 300 this todo's address is clear of the row where the engine's scroll leaves it, and the check there reads both)
    if (a && first) box.scrollTop += first.top - (box.getBoundingClientRect().top + box.clientTop);
    const again = a ? (a.getClientRects()[0] || a.getBoundingClientRect()) : null;
    const atLink2 = again ? d.elementFromPoint((again.left + again.right) / 2, (again.top + again.bottom) / 2) : null;
    const linkHitScrolled = !a ? "no-link" : atLink2 === a ? "target" : atLink2 ? ((atLink2 as HTMLElement).className || atLink2.tagName).split(" ")[0] : "none";
    detail.scrollTop = 30; const detailScrolls = detail.scrollTop > 0; detail.scrollTop = 0;
    box.scrollTop = box.scrollHeight;   // to the bottom, where the buttons are
    const out = { frameH: win.innerHeight, tight: overlay.classList.contains("kb-tight"), detailH: detail.clientHeight, detailLineH: parseFloat(win.getComputedStyle(detail).lineHeight),
      detailScrolls, linkHit, linkHitScrolled, boxScrollH: box.scrollHeight, boxClientH: box.clientHeight, boxScrollTop: box.scrollTop, sendHitAtBottom: hit(send), sendInBoxAtBottom: inBox(send) };
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
  // the click that ends a drag of the grip (the author's pass after the maintainer's round 1, composition-2): the grip pulled
  // past the box's bottom edge and released over the backdrop. At 508 the box is at its cap, so it cannot grow with the answer
  // box and the pointer leaves it; Chromium and WebKit dispatch the click to the overlay, the common ancestor of the press and
  // the release, Firefox to the textarea. Every click on the frame's document is recorded in the capture phase, so the record
  // names the click's target per engine. Where the headless grip does not move, the inline height is written under the press,
  // as the grip writes it, before the release; the road is reported
  const dragRelease = async (past = 30) => {
    await page.evaluate(() => {
      const w = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow! as any;
      w.__clicks = [];
      if (!w.__clickRec) { w.__clickRec = true; w.document.addEventListener("click", (e: any) => { w.__clicks.push(String(e.target.id || e.target.className || e.target.tagName).split(" ")[0]); }, true); }
    });
    const before = (await measure())!;
    const r = await page.evaluate(() => {
      const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
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
      await page.evaluate((h: number) => { const win = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!; (win.document.querySelector("#ut-reply-prompt .ut-reply-input") as HTMLElement).style.height = h + "px"; }, before.inputH + 60);
      await settle();
    }
    await page.mouse.up();
    await settle();
    await page.waitForTimeout(300);
    const after: { overlayUp: boolean; value: string | null; clicks: string[]; posted: number } = await page.evaluate(() => {
      const w = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow! as any; const d = w.document;
      const i = d.querySelector("#ut-reply-prompt .ut-reply-input") as HTMLTextAreaElement | null;
      return { overlayUp: !!d.getElementById("ut-reply-prompt"), value: i ? i.value : null, clicks: w.__clicks as string[], posted: (w.__posted || []).filter((p: any) => p && p.type === "userTodoAnswer").length };
    });
    return { road, endY: r.boxBottom + past, boxBottom: r.boxBottom, inputStyleHMid: mid.inputStyleH, ...after };
  };
  // a text selection dragged out of the box (the reviewer's ruling on the pass's observation): the press inside the textarea's
  // text, the pointer dragged past the box's bottom edge and released over the backdrop; the same common-ancestor click as the
  // grip's, with the box's height unchanged. The clicks are recorded as for the pull
  const selectRelease = async (past = 20) => {
    await page.evaluate(() => { const w = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow! as any; w.__clicks = []; });
    const r = await page.evaluate(() => {
      const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
      const i = d.querySelector("#ut-reply-prompt .ut-reply-input")!.getBoundingClientRect(); const b = d.querySelector("#ut-reply-prompt .confirm-box")!.getBoundingClientRect();
      return { left: i.left, top: Math.max(i.top, b.top), boxBottom: b.bottom };
    });
    await page.mouse.move(r.left + 20, r.top + 12);
    await page.mouse.down();
    await page.mouse.move(r.left + 60, r.boxBottom + past, { steps: 10 });
    await page.mouse.up();
    await settle();
    await page.waitForTimeout(300);
    const after: { overlayUp: boolean; value: string | null; clicks: string[] } = await page.evaluate(() => {
      const w = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow! as any; const d = w.document;
      const i = d.querySelector("#ut-reply-prompt .ut-reply-input") as HTMLTextAreaElement | null;
      return { overlayUp: !!d.getElementById("ut-reply-prompt"), value: i ? i.value : null, clicks: w.__clicks as string[] };
    });
    return { endY: r.boxBottom + past, ...after };
  };
  // a plain tap on the backdrop, above the box
  const tapBackdrop = async () => {
    const top: number = await page.evaluate(() => (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document.querySelector("#ut-reply-prompt .confirm-box")!.getBoundingClientRect().top);
    const at = { x: PHONE_W / 2, y: Math.max(4, Math.round(top / 2)) };
    await page.mouse.click(at.x, at.y);
    await settle();
    await page.waitForTimeout(200);
    const overlayUp: boolean = await page.evaluate(() => !!(document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document.getElementById("ut-reply-prompt"));
    return { at, overlayUp };
  };
  // THE REVERSE ROADS (the maintainer's round 2, ui-1): a press on the backdrop released inside the sheet. The points the
  // gestures use, read from the open sheet in the frame's coordinates (the frame sits at the page's origin, so they are the
  // page's too): the backdrop above the box, the answer box's and the title's centres, the box's left edge and top
  const points = () => page.evaluate(() => {
    const o = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document.getElementById("ut-reply-prompt")!;
    const b = o.querySelector(".confirm-box")!.getBoundingClientRect();
    const c = (sel: string) => { const r = o.querySelector(sel)!.getBoundingClientRect(); return { x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2 }; };
    return { back: { x: (b.left + b.right) / 2, y: Math.max(4, b.top / 2) }, input: c(".ut-reply-input"), title: c(".confirm-title"), boxLeft: b.left, boxTop: b.top };
  });
  // what the sheet did: is it still up, what its answer box holds, and how many answers the pane posted
  const sheetState = () => page.evaluate(() => {
    const w = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow! as any; const d = w.document;
    const i = d.querySelector("#ut-reply-prompt .ut-reply-input") as HTMLTextAreaElement | null;
    return { up: !!d.getElementById("ut-reply-prompt"), value: i ? i.value : null, posted: (w.__posted || []).filter((p: any) => p && p.type === "userTodoAnswer").length as number };
  });
  // a mouse press at one point, moved to another and released there
  const mouseDrag = async (from: { x: number; y: number }, to: { x: number; y: number }) => {
    await page.mouse.move(from.x, from.y); await page.mouse.down(); await page.mouse.move(to.x, to.y, { steps: 8 }); await page.mouse.up();
    await settle(); await page.waitForTimeout(300);
  };
  // a finger, through the DevTools protocol's touch input (Chromium only; Playwright drives no touch moves in Firefox or WebKit):
  // touched down at the first point, moved in six steps to the last, lifted there. Real touch events, so the engine applies its
  // own tap slop, gesture detection and implicit pointer capture
  let cdp: any = null;
  const touch = async (path: Array<{ x: number; y: number }>) => {
    if (!cdp) cdp = await page.context().newCDPSession(page);
    const at = (p: { x: number; y: number }) => [{ x: p.x, y: p.y, id: 1, radiusX: 1, radiusY: 1, force: 1 }];
    await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: at(path[0]) });
    for (let k = 1; k < path.length; k++) for (let s = 1; s <= 6; s++) {
      const a = path[k - 1], b = path[k];
      await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: at({ x: a.x + (b.x - a.x) * s / 6, y: a.y + (b.y - a.y) * s / 6 }) });
    }
    await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await settle(); await page.waitForTimeout(300);
  };
  // THE WORST CASE (the maintainer's round 2 ruling, B-i). The frame's width is an input too: 390, the phone, or 320, the
  // narrowest the composition uses
  const setWidth = async (w: number) => {
    await page.evaluate((ww: number) => { (document.getElementById("f-waiting") as HTMLIFrameElement).style.width = ww + "px"; }, w);
    await page.waitForFunction((ww: number) => (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.innerWidth === ww, w, { timeout: 10000 });
    await settle();
  };
  // Send against the box's CLIP (its padding box: the border box less the borders, where content past the edge is cut and
  // not hit-testable) and the frame; what a finger at Send's centre reaches; the answer box's height against a three-row probe;
  // and the answer box's last row (its bottom less the padding and border, one line tall: where the caret sits after typing at
  // the end) against the clip and the kept actions row's top; and the kept row's computed background against the box's (the row
  // is painted in the box's own colour, so what scrolls under it is hidden rather than seen through it)
  const cellRead = () => page.evaluate(() => {
    const win = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!; const d = win.document;
    const o = d.getElementById("ut-reply-prompt"); if (!o) return null;
    const box = o.querySelector(".confirm-box") as HTMLElement, input = o.querySelector(".ut-reply-input") as HTMLTextAreaElement, actions = o.querySelector(".confirm-actions") as HTMLElement;
    const send = actions.querySelectorAll("button")[1] as HTMLElement;
    const b = box.getBoundingClientRect(), sr = send.getBoundingClientRect(), ir = input.getBoundingClientRect();
    const clipTop = b.top + box.clientTop, clipBottom = clipTop + box.clientHeight;
    const cx = (sr.left + sr.right) / 2, cy = (sr.top + sr.bottom) / 2, at = d.elementFromPoint(cx, cy);
    const cs = win.getComputedStyle(input), lh = parseFloat(cs.lineHeight) || 18;
    const rowBottom = ir.bottom - parseFloat(cs.paddingBottom) - parseFloat(cs.borderBottomWidth);
    const probe = d.createElement("textarea"); probe.className = "ut-reply-input"; probe.rows = 3;
    probe.style.position = "fixed"; probe.style.top = "0"; probe.style.left = "0"; probe.style.width = "300px"; probe.style.visibility = "hidden";
    d.body.appendChild(probe); const floorH = probe.clientHeight; probe.remove();
    return { frameW: win.innerWidth, frameH: win.innerHeight, clipTop, clipBottom, sendTop: sr.top, sendBottom: sr.bottom, cx, cy,
      hit: at === send ? "target" : at === o ? "overlay" : at === box ? "box" : at ? ((at as HTMLElement).className || at.tagName).split(" ")[0] : "none",
      inputH: input.clientHeight, floorH, rowTop: rowBottom - lh, rowBottom, actionsTop: actions.getBoundingClientRect().top, inputStyleH: input.style.height,
      boxScrollTop: box.scrollTop, over: box.scrollHeight - box.clientHeight, rowBg: win.getComputedStyle(actions).backgroundColor, boxBg: win.getComputedStyle(box).backgroundColor };
  });
  // one cell: the sheet opened on `tid` with the keyboard up at h ("up"), or at rest at 732 and the keyboard then raised to h
  // ("order", the phone's order), the answer typed (fourteen lines, then a keystroke at its end); or, with the keyboard up at h,
  // the answer typed and the grip then pulled 150px down ("drag": a drag fires no input, so grow does not run after it; where the
  // headless grip does not move, the inline height is written as the grip writes it). Then Send read and a real click at its
  // centre, and what the click did: the answers posted for this todo, and whether the sheet is still up
  const sendCell = async (tid: string, h: number, how: "up" | "order" | "drag") => {
    await feed();
    await W.locator(`.ut-reply[data-tid="${tid}"]`).waitFor({ timeout: 10000 });
    if (how === "order") { await setHeight(APP_PANE, false); await openReply(tid); await setHeight(h, true); }
    else { await setHeight(h, true); await openReply(tid); }
    const typed = ANSWER(14) + (how === "drag" ? "" : " ok");
    const box = W.locator("#ut-reply-prompt .ut-reply-input");
    await box.fill(ANSWER(14));
    let road = "";
    if (how === "drag") {
      await settle();
      const g = await page.evaluate(() => { const r = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document.querySelector("#ut-reply-prompt .ut-reply-input")!.getBoundingClientRect(); return { x: r.right - 3, y: r.bottom - 3, h: r.height }; });
      await page.mouse.move(g.x, g.y); await page.mouse.down(); await page.mouse.move(g.x, g.y + 150, { steps: 10 }); await page.mouse.up();
      await settle();
      const after = await page.evaluate(() => (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document.querySelector("#ut-reply-prompt .ut-reply-input")!.getBoundingClientRect().height);
      road = "native grip";
      if (after < g.h + 30) {
        road = "scripted (the headless grip did not move)";
        await page.evaluate((hh: number) => { ((document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document.querySelector("#ut-reply-prompt .ut-reply-input") as HTMLElement).style.height = hh + "px"; }, Math.round(g.h + 150));
      }
    } else {
      await box.focus();
      await page.keyboard.press(browserName === "webkit" ? "Meta+ArrowDown" : "Control+End");
      await page.keyboard.type(" ok");
    }
    await settle();
    const m = await cellRead();
    const postedBefore: number = await page.evaluate(() => ((document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow! as any).__posted.length);
    if (m && m.cy >= 0 && m.cy <= m.frameH) await page.mouse.click(m.cx, m.cy);
    await settle(); await page.waitForTimeout(150);
    const after: { up: boolean; posted: string[] } = await page.evaluate(([t, n]: [string, number]) => {
      const w = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow! as any;
      return { up: !!w.document.getElementById("ut-reply-prompt"), posted: w.__posted.slice(n).filter((p: any) => p && p.type === "userTodoAnswer" && p.todoId === t).map((p: any) => String(p.text)) };
    }, [tid, postedBefore] as [string, number]);
    if (after.up) await page.evaluate(() => { const o = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document.getElementById("ut-reply-prompt"); (o!.querySelector(".confirm-actions button") as HTMLElement).click(); });
    return { m, typed, road, ...after };
  };
  return { page, W, setHeight, setResizesContent, restoreShell, settle, measure, probeShort, openReply, cancelReply, fill, tapSend, dragTaller, dragRelease, selectRelease, tapBackdrop, waitTight, points, sheetState, mouseDrag, touch, setWidth, sendCell, errors };
}
// a short window with the chip todo open: the box scrolls; the detail keeps its floor and scrolls within itself; its
// first line's address and Send are each under a finger once the box is scrolled to them (the address's line to the top of
// the box's view: the kept actions row covers the box's bottom). With `strict` (300px) the address is also under a finger
// where the engine's own scroll left it: the maintainer's round 2 accepted the kept row's cover of that address at 230 only
function assertShort(s: Short, what: string, strict = false) {
  const rec = JSON.stringify(s);
  assert.equal(s.tight, true, `${what}: under the fold (${rec})`);
  assert.ok(s.detailH >= floorOf(s.detailLineH), `${what}: the detail keeps its floor of two lines (${s.detailH}px against a ${s.detailLineH}px line); without the floor it resolved to 0px, invisible and unscrollable (${rec})`);
  assert.ok(s.detailScrolls, `${what}: the detail scrolls within itself (${rec})`);
  if (strict) assert.equal(s.linkHit, "target", `${what}: the address on the detail's first line is under a finger where the engine's own scroll left it (scrollIntoView nearest), not under the kept actions row: the maintainer's round 2 accepted the row's cover of that address at 230 only (${rec})`);
  assert.equal(s.linkHitScrolled, "target", `${what}: the address on the detail's first line is under a finger once the box is scrolled to bring its line to the top of the box's view (where the engine's own scroll left it, a finger reached ${s.linkHit}: the kept actions row covers the box's bottom) (${rec})`);
  assert.ok(s.boxScrollH > s.boxClientH + 1 && s.boxScrollTop > 0, `${what}: the box scrolls: the floors alone overflow this window, and the deficit past them is a scroll of the box, never a clip (${rec})`);
  assert.ok(s.sendInBoxAtBottom && s.sendHitAtBottom === "target", `${what}: scrolled to the box's bottom, Send is inside the clip and under a finger (${rec})`);
}

// Send is INSIDE the box's clip (its rect within the box's rect) and inside the frame, so a finger on it reaches it. The
// box's rect is its clip: overflow hidden or auto, content past its edges is not hit-testable
// the alpha of a computed background-color: engines serialize it as rgb() (alpha 1) or rgba(), and transparent as
// rgba(0, 0, 0, 0); any other form reads as NaN, which no check passes
const alphaOf = (c: string): number => {
  const v = c.trim(); if (v === "transparent") return 0;
  const m = /^rgba?\(([^)]*)\)$/.exec(v); if (!m) return NaN;
  const p = m[1].split(/[\s,\/]+/).filter(Boolean);
  return p.length === 3 ? 1 : p.length === 4 ? parseFloat(p[3]) : NaN;
};
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
  test(`in ${name}: with the keyboard up the answer box holds three rows, the detail scrolls within its cap, and Cancel and Send stay in the frame; the fold follows the frame's height`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension, and the browser legs need it; none of CI's browser-backed steps runs this leg, and the served leg tests/test_reply_sheet_served.py runs this composition in CI's Browser-backed served-page tests (pytest) step"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box, and this leg needs it; none of CI's browser-backed steps runs this leg, and the served leg tests/test_reply_sheet_served.py is the guard where this skips (CI's Browser-backed served-page tests (pytest) step runs it in chromium): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { page, W, setHeight, settle, measure, probeShort, openReply, cancelReply, fill, dragTaller, dragRelease, selectRelease, tapBackdrop, waitTight, errors } = await boot(browser);
      await openReply("t1");
      // ── 508px: the keyboard up on a phone, above the fold's threshold: the squeeze fix alone
      let m = (await measure())!;
      assert.ok(m, "the Reply sheet is up");
      assert.equal(m.frameH, KEYBOARD_UP, "the frame is the phone's visible height with the keyboard up");
      assert.equal(m.tight, false, "508px is not a short window: no fold, so what follows is the squeeze fix on its own");
      assert.ok(m.floorH > 30, `the probe laid out three rows (${m.floorH}px; line-height ${m.lineHeight})`);
      assert.ok(m.inputH >= m.floorH - 1, `the answer box holds three rows: ${m.inputH}px against the ${m.floorH}px three-row probe (on the base tree it was a 14px sliver in Chromium and WebKit, the textarea taking the whole deficit; Firefox kept the rows there, so the detail's overflow-y assertion below is its first red, and the base tree's red in all three engines)`);
      assert.equal(m.detailOverflowY, "auto", "the detail scrolls within itself (the base tree computes visible in Chromium, Firefox and WebKit alike: the red common to the three engines, reached first in Firefox, where the textarea kept its rows and the buttons stayed in reach; there the focus had scrolled the overflow-hidden box to the textarea, so the title, the ask and most of the detail sat above the clip with no way to scroll back, in every engine)");
      assert.ok(m.detailScrolls, "the overflow declaration is LIVE: the detail's scrollTop moves (with overflow visible it stays at 0, and the detail's text paints over the answer box); the rule pin reads the sheet with comments stripped, this reads the engine");
      assert.ok(m.detailScrollH > m.detailClientH + 8, `the forty-line detail overflows its cap and is a scroll away, not clipped (${m.detailClientH} of ${m.detailScrollH}px)`);
      assert.ok(m.detailScrollW <= m.detailOffsetW, `no sideways scroller: the unbreakable token in the detail wraps inside the box (overflow-wrap: anywhere), so the detail's content is no wider than its border box (scrollWidth ${m.detailScrollW} against offsetWidth ${m.detailOffsetW}; the widest text rect ends at ${m.detailTextRight.toFixed(1)} against the detail's ${m.detailRight.toFixed(1)}px, a figure a trailing space hanging at a soft wrap pushes a few pixels past the edge, so it is not the bar); without the wrap the token ran hundreds of pixels past it and a scroll container's overflow-x, computing to auto, scrolled sideways`);
      assert.equal(m.detailOverflowX, "hidden", "overflow-x: hidden, #pinned-notes's companion declaration, so a token the wrap cannot break is clipped, never a sideways scroll");
      assert.ok(m.detailClientH > 20, `the detail still shows some lines (${m.detailClientH}px): the box gave way, not the whole detail`);
      assert.ok(m.actionsBottom > 0 && m.actionsBottom <= m.frameH + 0.5, `Cancel and Send are inside the frame (bottom edge ${m.actionsBottom.toFixed(1)} of ${m.frameH}px)`);
      assert.ok(m.boxBottom <= m.frameH + 0.5, `the whole box is inside the frame (${m.boxBottom.toFixed(1)} of ${m.frameH}px)`);
      assert.equal(m.boxOverflowY, "auto", "the box scrolls at this height too, not only under the fold: the every-height backstop (#ut-reply-prompt .picker-box)");
      // ── 420px: a short window: the fold, on the frame's own resize event
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
      // ── 900px: the keyboard down: the same event takes the fold off
      await setHeight(TALL);
      await waitTight(false);
      m = (await measure())!;
      assert.equal(m.tight, false, "the room back, the fold comes off");
      assert.notEqual(m.alignItems, "flex-start", "the sheet centers again (.confirm-overlay)");
      assert.ok(m.inputH >= m.floorH - 1, `tall, the answer box holds three rows (${m.inputH} against ${m.floorH}px)`);
      assert.ok(m.actionsBottom <= m.frameH + 0.5, "the buttons are inside the frame");
      // the cap at rest, where nothing squeezes: the larger of 12em and 34.8% of the window's height, here the viewport term
      // (313.2px at 900 against 12em's 134px), executed rather than a spelling; the keyboard-up heights above are the shrink and
      // the floor under a 12em cap (the detail's cap at rest has its own test below)
      assert.ok(Math.abs(m.detailClientH - Math.max(12 * m.detailFontPx, REST_SHARE * m.frameH)) <= 1.5, `tall, the keyboard down: the forty-line detail sits at its cap at rest, 34.8% of the window's height: ${m.detailClientH}px against ${(REST_SHARE * m.frameH).toFixed(1)}px (12em of its ${m.detailFontPx}px font is ${(12 * m.detailFontPx).toFixed(1)}px, the head's cap)`);
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
      assertShort(await probeShort(), "300px, the chip todo", true);
      await setHeight(230);
      assertShort(await probeShort(), "230px, the chip todo");
      // ── 420px with the chip todo (the fold on): the pane's two chip rows put the floors alone past the fold's cap, so the box
      // scrolls the difference (about 19px) and the actions row, kept in view at the box's bottom, holds Cancel and Send inside
      // the clip, at open and with fourteen lines typed; scrolled to the bottom Send is inside the clip too. Before the kept row
      // Send's bottom edge lay 2 to 3px past the clip here (its centre still under a finger with this ask at 390 wide; a longer
      // ask or a narrower phone put the centre past it, THE WORST CASE test below). The chat's column has no chip rows and fits here (render-reply-sheet-browser.test.ts
      // asserts the fitted state). A chrome change that closes or widens the deficit is loud here, so the body's account of
      // this window stays true
      await setHeight(KEYBOARD_TIGHT);
      m = (await measure())!;
      assert.equal(m.tight, true, "420px with the chip todo: under the fold");
      assert.ok(m.detailClientH >= floorOf(m.detailLineH), `420px, the chip todo, at open: the detail keeps its floor of two lines (${m.detailClientH}px against a ${m.detailLineH}px line)`);
      assert.ok(m.boxScrollH > m.boxClientH + 1 && m.boxScrollH - m.boxClientH < 40, `420px, the chip todo, at open: the pane's floors alone overflow the fold's cap by a few pixels (${m.boxScrollH} of ${m.boxClientH}px): two chip rows the chat's column does not have, and the box scrolls the difference with the actions row kept in view; a chrome change that makes the pane fit here, or overflow by more, changes what the body says of this window (${where(m)})`);
      assert.equal(m.boxOverflowY, "auto", "420px, the chip todo: the box scrolls");
      assert.ok(boxInsideFrame(m), `420px, the chip todo: the box is inside the frame (${where(m)})`);
      assert.ok(sendInsideBox(m) && cancelInsideBox(m), `420px, the chip todo, at open: Cancel and Send are inside the box's clip, the actions row kept in view at its bottom (before it, Send's bottom edge lay 2 to 3px past the clip here) (${where(m)})`);
      assert.equal(m.hitAtSend, "target", `420px, the chip todo, at open: Send's centre is under a finger (${where(m)})`);
      let s = await probeShort();
      assert.ok(s.sendInBoxAtBottom && s.sendHitAtBottom === "target", `420px, the chip todo, at open: scrolled to the box's bottom, Send is inside the clip and under a finger (${JSON.stringify(s)})`);
      await fill(ANSWER(14));
      m = (await measure())!;
      assert.ok(m.inputH >= m.floorH - 1, `420px, the chip todo, fourteen lines: three rows still (${m.inputH} against ${m.floorH}px); the room is nothing here, so the answer scrolls inside its box`);
      assert.ok(m.detailClientH >= floorOf(m.detailLineH), `420px, the chip todo, fourteen lines: the detail keeps its floor (${m.detailClientH}px against a ${m.detailLineH}px line)`);
      assert.ok(sendInsideBox(m) && cancelInsideBox(m), `420px, the chip todo, fourteen lines: Cancel and Send are inside the box's clip, the actions row kept in view (${where(m)})`);
      assert.equal(m.hitAtSend, "target", `420px, the chip todo, fourteen lines: Send's centre is under a finger (${where(m)})`);
      s = await probeShort();
      assert.ok(s.sendInBoxAtBottom && s.sendHitAtBottom === "target", `420px, the chip todo, fourteen lines: scrolled to the box's bottom, Send is inside the clip and under a finger (${JSON.stringify(s)})`);
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
      await page.evaluate(() => { const win = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!; (win.document.querySelector("#ut-reply-prompt .ut-reply-input") as HTMLElement).style.height = "215px"; });
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
      // ── a click whose press began inside the sheet is not a backdrop tap (the author's pass after the maintainer's round 1,
      // composition-2, and the reviewer's ruling on the selection: a backdrop tap is press and release both on the backdrop). At
      // 508 the box is at its cap, so a grip pull released past its bottom edge, or a text selection dragged out of the box, leaves
      // the pointer over the backdrop; Chromium and WebKit dispatch that click to the overlay, the common ancestor of the press and
      // the release, and before the guard it closed the sheet with the answer (Firefox retargets the click to the textarea). The
      // sheet stands with its text after either gesture in every engine, and a plain tap on the backdrop still dismisses (what a
      // dismiss does is the filed discard item's)
      await fill(ANSWER(3));
      const rel = await dragRelease();
      t.diagnostic(`${name}: the drag's release: ${rel.road}; released at y ${rel.endY.toFixed(1)}, past the box's bottom ${rel.boxBottom.toFixed(1)}; the clicks' targets ${JSON.stringify(rel.clicks)}`);
      assert.equal(rel.overlayUp, true, `a click whose press began inside the sheet is not a backdrop tap: the sheet stands after a grip drag released over the backdrop (${rel.road}; the clicks' targets ${JSON.stringify(rel.clicks)}); before the guard Chromium and WebKit closed it with the answer; Firefox retargets the click to the textarea`);
      assert.equal(rel.value, ANSWER(3), "and the answer is intact");
      assert.equal(rel.posted, 0, "the release posted nothing");
      const sel = await selectRelease();
      t.diagnostic(`${name}: the selection's release: from inside the textarea to y ${sel.endY.toFixed(1)}; the clicks' targets ${JSON.stringify(sel.clicks)}`);
      assert.equal(sel.overlayUp, true, `a text selection dragged out of the box and released over the backdrop (the clicks' targets ${JSON.stringify(sel.clicks)}) is not a backdrop tap either: the sheet stands (before the widened predicate Chromium and WebKit closed it with the answer, the same common-ancestor click with the box's height unchanged; Firefox retargets the click to the textarea)`);
      assert.equal(sel.value, ANSWER(3), "and the answer is intact through the selection's release");
      const tapped = await tapBackdrop();
      assert.equal(tapped.overlayUp, false, `a plain tap on the backdrop (at ${tapped.at.x}, ${tapped.at.y}) still dismisses; what a dismiss does with the text is the filed discard item's, untouched here`);
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

  // THE DETAIL'S CAP AT REST AND UNDER THE KEYBOARD (the maintainer's ruling at the merge with main), its own test so
  // each regime has its own red: with the keyboard down the cap is the larger of 12em and 34.8% of the window's height;
  // with the keyboard up it is 12em, as at the head. Which term binds: 34.8% of the window passes 12em (134.16px at the
  // detail's 11.18px font) above about 386px, so at rest the viewport term binds at every phone pane (215.8px at 620,
  // 254.7px at the installed app's 732), at 900 (313.2px) and at 1080 (375.8px), and 12em at 300 (34.8% is 104.4px),
  // where the room, not the cap, sets the rendered height, so the computed max-height is what shows which arm won; under
  // the keyboard the term is withdrawn and 12em binds (at 508 the room would hold 174px, so a cap that let the term in
  // there shows as a taller detail). The share is derived at the pane heights a phone gives (the maintainer's rulings on
  // the cap pass and on the share; styles.css has the derivation): Safari's 620, 633 (the common pane) and 709, and the
  // installed app's 732, where the share holds the two properties it was chosen for: the tightest sheet (t2: both chip
  // rows, the wrapped ask, the forty-one-line detail) at its cap, under its room, read as the detail's laid-out height
  // against the resolved cap (a share past the band makes the room the smaller), and the recorded 8-line detail (t4) in
  // full. In Safari's panes the tightest sheet (both chip rows) has less room than the cap, so it fits with its detail
  // under the cap, and the 8-line detail shows the cap and scrolls the rest. The stated boundary is a 720px pane (717 in
  // WebKit, 718 in Firefox): the 8-line detail is pinned in full at 720 and not in full one pixel under each engine's own
  // boundary, so a share that moves the boundary is named as that.
  // This leg lays the sheet out in the box's fallback font (the served stylesheet's font urls 404 here), where the pane's
  // chip sheet has a pixel more room than in the served shell, so a share a hair past the band can pass here: the served
  // leg tests/test_reply_sheet_served.py reads the same pins with the webfont loaded, in CI
  test(`in ${name}: the detail's cap at rest is the larger of 12em and 34.8% of the window's height (the viewport term at the phone panes, 900 and 1080, 12em at 300), and 12em under the keyboard, as at the head`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension, and the browser legs need it; none of CI's browser-backed steps runs this leg, and the served leg tests/test_reply_sheet_served.py measures the cap at rest and under the keyboard in CI's Browser-backed served-page tests (pytest) step"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box, and this leg needs it; none of CI's browser-backed steps runs this leg, and the served leg tests/test_reply_sheet_served.py is the guard where this skips (CI's Browser-backed served-page tests (pytest) step runs it in chromium): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { setHeight, setResizesContent, restoreShell, measure, openReply, cancelReply, waitTight, errors } = await boot(browser);
      const em12 = (m: Sheet) => 12 * m.detailFontPx;
      const term = (m: Sheet) => REST_SHARE * m.frameH;
      const below = BELOW_BOUNDARY[name];
      // at rest, the viewport term the larger: the resolved cap and the forty-line detail's height are 34.8% of the window
      const atRestTerm = (m: Sheet, what: string) => {
        assert.equal(m.tight, false, `${what}: no fold`);
        assert.ok(term(m) > em12(m) + 20, `${what}: 34.8% of the window (${term(m).toFixed(1)}px) is the larger term against 12em (${em12(m).toFixed(1)}px)`);
        assert.ok(Math.abs(m.detailMaxH - term(m)) <= 0.5, `${what}: the cap is 34.8% of the window's height (${m.detailMaxH}px against ${term(m).toFixed(1)}px); the head's cap was 12em at every height (${em12(m).toFixed(1)}px)`);
        assert.ok(Math.abs(m.detailClientH - term(m)) <= 1.5, `${what}: the long detail shows at the cap, ${m.detailClientH}px against ${term(m).toFixed(1)}px (${m.detailScrollH}px of it)`);
        assert.ok(m.inputH >= m.floorH - 1, `${what}: the answer box holds three rows (${m.inputH} against ${m.floorH}px)`);
        assertFits(m, what);
      };
      // each window is its own subtest, so each pin reports its own red or green; they run in order on one page, and a sheet
      // a subtest opens is closed in its finally so the next one opens its own
      await t.test("at rest at 900: the viewport term (the forty-line detail)", async () => {
        await setHeight(TALL, false);
        await openReply("t1");
        atRestTerm((await measure())!, "at rest at 900, the forty-line detail");
      });
      await t.test("the keyboard up at 508 under the open sheet: 12em, as at the head", async () => {
        await setHeight(KEYBOARD_UP, true);
        const m = (await measure())!;
        assert.equal(m.tight, false, "508px: no fold, so the cap is the only change the keyboard makes to the detail here");
        assert.ok(Math.abs(m.detailMaxH - em12(m)) <= 0.5, `the keyboard up at 508: the cap is 12em (${m.detailMaxH}px against ${em12(m).toFixed(1)}px), no viewport term (34.8% of 508 would be ${term(m).toFixed(1)}px)`);
        assert.ok(Math.abs(m.detailClientH - em12(m)) <= 1.5, `the keyboard up at 508: the forty-line detail shows 12em (${m.detailClientH}px), its height at the head; a cap that let the viewport term in would show it taller here, up to the room the box has`);
        assert.ok(m.inputH >= m.floorH - 1, `the keyboard up at 508: three rows (${m.inputH} against ${m.floorH}px)`);
        assertFits(m, "the keyboard up at 508");
      });
      await t.test("the keyboard down again at 900: the viewport term is back", async () => {
        await setHeight(TALL, false);
        atRestTerm((await measure())!, "the keyboard down again at 900");
      });
      await t.test("at rest at 1080, a tall window: the viewport term", async () => {
        await setHeight(REST_TALL, false);
        atRestTerm((await measure())!, "at rest at 1080");
      });
      await t.test("at rest at 300, a window short enough that 12em is the larger term", async () => {
        try {
          await setHeight(REST_SHORT, false);   // the fold is on: a short window, not the keyboard
          await waitTight(true);
          const m = (await measure())!;
          assert.ok(term(m) < em12(m) - 20, `at rest at 300: 12em (${em12(m).toFixed(1)}px) is the larger term against 34.8% of the window (${term(m).toFixed(1)}px)`);
          assert.ok(Math.abs(m.detailMaxH - em12(m)) <= 0.5, `at rest at 300: the cap is 12em (${m.detailMaxH}px against ${em12(m).toFixed(1)}px): the max's other arm, executed at rest`);
          assert.ok(m.detailClientH <= m.detailMaxH + 0.5 && m.detailClientH >= floorOf(m.detailLineH), `at rest at 300: the room, under the cap, sets the detail's height, never under its floor (${m.detailClientH}px)`);
        } finally { await cancelReply(); }
      });
      // the phone panes at rest: the forty-line detail at the viewport term (a short ask leaves the room over the cap)
      for (const h of [SAFARI_16E, SAFARI_BARS, SAFARI_TOP, APP_PANE]) {
        await t.test(`at rest at ${h}, a phone pane: the viewport term (the forty-line detail)`, async () => {
          await setHeight(h, false);   // no sheet is up: the next one opens at this height
          await openReply("t1");
          try { atRestTerm((await measure())!, `at rest at ${h}, the forty-line detail`); }
          finally { await cancelReply(); }
        });
      }
      // Safari's panes: the tightest sheet (both chip rows) has less room than the cap here, so it fits with its detail under the cap and over its floor
      for (const h of [SAFARI_16E, SAFARI_BARS, SAFARI_TOP]) {
        await t.test(`at rest at ${h}, a Safari pane: the tightest sheet (both chip rows) fits, its detail under the cap`, async () => {
          await setHeight(h, false);
          await openReply("t2");
          try {
            const m = (await measure())!;
            const what = `at rest at ${h}, the tightest sheet (both chip rows)`;
            assert.equal(m.tight, false, `${what}: no fold`);
            assert.ok(Math.abs(m.detailMaxH - term(m)) <= 0.5, `${what}: the cap is 34.8% of the window's height (${m.detailMaxH}px against ${term(m).toFixed(1)}px)`);
            assert.ok(m.detailClientH <= m.detailMaxH + 1.5 && m.detailClientH >= floorOf(m.detailLineH), `${what}: the detail is under its cap and over its floor of two lines (${m.detailClientH}px under a ${m.detailMaxH}px cap, a ${m.detailLineH}px line); where the room is the smaller the shrink sets it`);
            assert.ok(m.inputH >= m.floorH - 1, `${what}: three rows (${m.inputH} against ${m.floorH}px)`);
            assertFits(m, what);
          } finally { await cancelReply(); }
        });
      }
      // the tightest sheet (both chip rows) at its cap, under its room, where the share holds that room: the installed app's pane, and 900. The room is
      // read as the detail's laid-out height against the resolved cap: at its cap they agree; a share whose cap passes the room
      // leaves the detail at the room, under the cap, and the flex shrink, not the cap, sets its height
      for (const h of [APP_PANE, TALL]) {
        await t.test(`at rest at ${h}: the tightest sheet (both chip rows) at its cap, under its room`, async () => {
          await setHeight(h, false);
          await openReply("t2");
          try {
            const m = (await measure())!;
            const what = `at rest at ${h}, the tightest sheet (both chip rows)`;
            assert.ok(Math.abs(m.detailMaxH - term(m)) <= 0.5, `${what}: the cap is 34.8% of the window's height (${m.detailMaxH}px against ${term(m).toFixed(1)}px)`);
            assert.ok(m.detailRectH >= m.detailMaxH - 0.5, `${what}: the detail is laid out at its cap (${m.detailRectH.toFixed(2)}px under a ${m.detailMaxH}px cap): the room is the smaller, so the share is past what this sheet's room holds at this pane (styles.css: up to 0.354 at the app's 732)`);
            atRestTerm(m, `${what}: the cap under its room`);
          } finally { await cancelReply(); }
        });
      }
      // the recorded 8-line detail under the stated boundary (styles.css: in full from a 720px pane, 717 in WebKit;
      // Firefox's own boundary, measured here, is 718): in Safari's panes and one pixel under the engine's own boundary it
      // shows the cap and scrolls the rest. It is read whole first, so a share that shows it in full here is named as the
      // boundary having moved
      for (const h of [SAFARI_16E, SAFARI_BARS, SAFARI_TOP, below]) {
        await t.test(`at rest at ${h}, under the stated boundary: the recorded 8-line detail shows the cap and scrolls the rest`, async () => {
          await setHeight(h, false);
          await openReply("t4");
          try {
            const m = (await measure())!;
            const what = `at rest at ${h}, the 8-line detail`;
            assert.ok(m.detailScrollH > em12(m) + 60, `the 8-line detail is longer than 12em (${m.detailScrollH}px against ${em12(m).toFixed(1)}px)`);
            assert.ok(m.detailClientH < m.detailScrollH, `${what}: not in full, ${m.detailClientH} of ${m.detailScrollH}px under a ${m.detailMaxH}px cap: the pane is under the stated boundary (in full from 720px, ${below + 1} in this engine); in full here, the share moved the boundary that styles.css and the ledger entry state`);
            assert.ok(Math.abs(m.detailClientH - term(m)) <= 1.5, `${what}: it shows at the cap, ${m.detailClientH}px against ${term(m).toFixed(1)}px`);
            assert.ok(m.inputH >= m.floorH - 1, `${what}: three rows (${m.inputH} against ${m.floorH}px)`);
            assertFits(m, what);
          } finally { await cancelReply(); }
        });
      }
      // …and in full at the boundary, at the installed app's pane and at 900, the answer box at three rows, Send inside the box
      for (const h of [BOUNDARY, APP_PANE, TALL]) {
        await t.test(`at rest at ${h}: the recorded 8-line detail shows in full, the answer box at three rows, Send inside the box`, async () => {
          await setHeight(h, false);   // no sheet is up: the next one opens at this height
          await openReply("t4");
          try {
            const m = (await measure())!;
            assert.ok(m.detailScrollH > em12(m) + 60, `the 8-line detail is longer than 12em (${m.detailScrollH}px against ${em12(m).toFixed(1)}px), so the head showed only part of it`);
            assert.ok(m.detailClientH >= m.detailScrollH, `at rest at ${h} the recorded 8-line detail shows in full: ${m.detailClientH} of ${m.detailScrollH}px under a ${m.detailMaxH}px cap (the head's 12em showed ${em12(m).toFixed(1)}px of it; the stated boundary is 720px)`);
            assert.ok(m.inputH >= m.floorH - 1, `at rest at ${h}, the 8-line detail: three rows (${m.inputH} against ${m.floorH}px)`);
            assertFits(m, `at rest at ${h}, the 8-line detail in full`);
          } finally { await cancelReply(); }
        });
      }
      // A STATED RESIDUAL of the keyboard-up ruling (the maintainer's ruling on the cap pass), pinned as it is so a change to
      // it is seen: under Android Chrome's resizes-content the keyboard shrinks the shell's layout viewport, so restCap, which
      // reads the keyboard on the shell as kbOpen does, sees none, and the at-rest term applies under the keyboard. The sheet
      // is opened at rest at 900 and the keyboard then raised under it to 508: the cap is 34.8% of 508 (176.8px) and not 12em
      // (134.16px), and the room (174px for the forty-line detail) sets the detail's height; the answer box keeps its three
      // rows and Send stays in the box. Under the iOS model above the same 508 is 12em
      await t.test("the keyboard up at 508 under Android Chrome's resizes-content: restCap sees no keyboard and the at-rest term applies, a stated residual", async () => {
        await setHeight(TALL, false);
        await openReply("t1");
        try {
          await setResizesContent(KEYBOARD_UP);
          const m = (await measure())!;
          const what = "the keyboard up at 508 under resizes-content";
          assert.equal(m.frameH, KEYBOARD_UP, `${what}: the pane is the shell's shrunk height`);
          assert.equal(m.tight, false, `${what}: no fold`);
          assert.ok(Math.abs(m.detailMaxH - term(m)) <= 0.5, `${what}: the cap is the at-rest term, 34.8% of the pane (${m.detailMaxH}px against ${term(m).toFixed(1)}px), not 12em (${em12(m).toFixed(1)}px): the residual restCap and the ledger entry state; a keyboard signal that survives resizes-content changes this, and what they say`);
          assert.ok(m.detailClientH > em12(m) + 20 && m.detailClientH <= m.detailMaxH + 0.5, `${what}: the forty-line detail shows more than 12em, up to the room (${m.detailClientH}px under a ${m.detailMaxH}px cap)`);
          assert.ok(m.inputH >= m.floorH - 1, `${what}: three rows (${m.inputH} against ${m.floorH}px)`);
          assertFits(m, what);
        } finally { await restoreShell(); await cancelReply(); }
      });
      assert.deepEqual(errors, [], "no script error in the frame");
    } finally { await browser.close(); }
  });

  // THE COMPOSITION, as its own test so the deciding figure has a red of its own: at 390 by 508 with the keyboard up, the
  // ask wrapped to several lines, both chips, the forty-line detail, the answer grown to the cap, a real click where Send is
  // painted. The tap's outcome is asserted FIRST: on the round-1 tree the grown answer box laid Send below the box's clip in
  // every engine, so the finger found the backdrop or nothing and the sheet closed with nothing posted, and that is the
  // assertion that goes red there, not a geometry read before it. On the base the tap sends in Chromium and Firefox and misses
  // only in WebKit, where a 14px answer box under the unshrinkable detail, in the focus-scrolled overflow-hidden box, leaves
  // Send below the clip; the base's red common to the three engines is the main test's overflow-y assertion. The geometry
  // follows, as the explanation of the outcome
  test(`in ${name}: THE COMPOSITION at 390 by 508 with the keyboard up: a tap where Send is painted sends the answer, and the sheet closes by the send, never by the backdrop`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension, and the browser legs need it; none of CI's browser-backed steps runs this leg, and the served leg tests/test_reply_sheet_served.py runs this composition in CI's Browser-backed served-page tests (pytest) step"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box, and this leg needs it; none of CI's browser-backed steps runs this leg, and the served leg tests/test_reply_sheet_served.py is the guard where this skips (CI's Browser-backed served-page tests (pytest) step runs it in chromium): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { measure, openReply, fill, tapSend, errors } = await boot(browser);
      await openReply("t2");
      const open = (await measure())!;
      await fill(ANSWER(14));
      const tap = await tapSend("t2");
      const rec = JSON.stringify({ tapAt: tap.tapAt, inFrame: tap.inFrame, hitAtSend: tap.before.hitAtSend, sendRect: tap.before.sendRect, box: [tap.before.boxTop, tap.before.boxBottom, tap.before.boxClientH, tap.before.boxScrollH, tap.before.boxOverflowY], inputH: tap.before.inputH, detailH: tap.before.detailClientH, detailLineH: tap.before.detailLineH, after: { overlayUp: tap.overlayUp, rowUp: tap.rowUp, posted: tap.posted } });
      assert.deepEqual(tap.posted.map((p) => [p.type, p.todoId, p.text.split("\n")[0]]), [["userTodoAnswer", "t2", "line 1"]], `composition: the tap SENT the answer (one userTodoAnswer posted); on the round-1 tree the finger found the backdrop (Firefox, and the chat in every engine) or nothing (the tap point off the frame) and nothing was posted (${rec})`);
      assert.equal(tap.rowUp, false, `composition: the answered todo's row is gone (dropTodo: the send happened, not a backdrop close) (${rec})`);
      assert.equal(tap.overlayUp, false, `composition: the sheet closed by the send itself (${rec})`);
      assert.ok(tap.inFrame, `composition: the tap point is inside the frame (${rec})`);
      assert.equal(tap.before.hitAtSend, "target", `composition: a finger at Send's painted centre reaches Send, not the backdrop (${rec})`);
      assert.ok(sendInsideBox(tap.before) && cancelInsideBox(tap.before), `composition: Cancel and Send are inside the box's clip (${where(tap.before)}); on the round-1 tree the answer box grown to 40% of the window laid them out below it`);
      assert.ok(boxInsideFrame(tap.before), `composition: the box is inside the frame (${where(tap.before)})`);
      assert.ok(tap.before.detailClientH >= floorOf(tap.before.detailLineH), `composition: with the answer grown to the cap the detail keeps its floor of two lines (${tap.before.detailClientH}px against a ${tap.before.detailLineH}px line); on the round-1 tree it resolved to 0px here (${rec})`);
      assert.deepEqual(open.kinds, ["confirm-title", "confirm-detail", "wt-file", "wt-link", "ut-detail", "ut-reply-input", "confirm-actions"], "the pane's sheet with both chips as flex children of the box (waiting.ts showReply; the chat's builder puts them inside the quoted line)");
      assert.equal(open.tight, false, "508px: no fold, so this is the room cap and the every-height scroll on their own");
      assert.deepEqual(errors, [], "no script error in the frame");
    } finally { await browser.close(); }
  });

  // THE REVERSE ROADS, as their own test (the maintainer's round 2, ui-1): a press on the backdrop released inside the sheet is
  // not a backdrop tap. The sheet's click line read only where the press began, and a click whose press and release targets
  // differ is dispatched to their common ancestor, which for a press on the overlay is the overlay itself in all three engines,
  // so a mouse pressed on the backdrop and released on the answer box or the title closed the sheet with the answer. A finger
  // is worse: a touch pointer is implicitly captured to the node it pressed, so its pointerup's target is the overlay wherever it
  // lifts, and reading the release's target alone still closed the sheet for a finger pressed just outside the box's edge and
  // lifted inside it; the builders give that capture back on a backdrop press (the ruling's form R2). Driven at 900 (at rest)
  // and 508 (the keyboard up), on the short ask with the forty-line detail and an answer typed: the mouse's reverse drags in
  // every engine; in Chromium a finger through the DevTools protocol's touch input, pressed 6px left of the box's edge and lifted
  // 6px inside it, and pressed 10px left of it and lifted 5px inside it (the ruling's two presses, taken as ruled: at the phone's
  // width the box's left edge is under 8px from the window's, so the 10px press lies just past the window's left edge, a point
  // the protocol accepts and Chromium delivers to the overlay, as the ruling's own measurement took it), at the answer
  // box's height (touch in Firefox and WebKit, and on iOS, is a stated residual: Playwright drives no touch moves there); after each the sheet stands with the answer and nothing is
  // posted. At the head before this fix every one of these closed the sheet with the answer. Then a plain tap on the backdrop
  // still dismisses: the mouse's in every engine, a finger's in Chromium
  test(`in ${name}: a press on the backdrop released inside the sheet is not a backdrop tap (the mouse's reverse drags${name === "chromium" ? ", and a finger pressed just outside the box's edge and lifted inside it" : ""}), at 900 and 508; a plain tap on the backdrop still dismisses`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension, and the browser legs need it; none of CI's browser-backed steps runs this leg, and the served leg tests/test_reply_sheet_served.py drives the touch road in CI's Browser-backed served-page tests (pytest) step"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box, and this leg needs it; none of CI's browser-backed steps runs this leg, and the served leg tests/test_reply_sheet_served.py is the guard where this skips (CI's Browser-backed served-page tests (pytest) step runs it in chromium): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { setHeight, openReply, cancelReply, fill, points, sheetState, mouseDrag, touch, errors } = await boot(browser);
      const TYPED = "my typed answer";
      // a sheet up with the answer typed: the one the last step left standing, or a fresh one where the last step closed it
      const ready = async () => {
        const st = await sheetState();
        if (!st.up) await openReply("t1");
        if (!st.up || st.value !== TYPED) await fill(TYPED);
      };
      if (name !== "chromium") t.diagnostic(`${name}: the touch road is a stated residual here: Playwright drives no touch moves in this engine (and iOS is unmeasured)`);
      for (const [h, kb] of [[TALL, false], [KEYBOARD_UP, true]] as Array<[number, boolean]>) {
        if ((await sheetState()).up) await cancelReply();
        await setHeight(h, kb);
        const roads: Array<[string, (p: Awaited<ReturnType<typeof points>>) => Promise<void>]> = [
          ["the mouse pressed on the backdrop and released on the answer box", (p) => mouseDrag(p.back, p.input)],
          ["the mouse pressed on the backdrop and released on the title", (p) => mouseDrag(p.back, p.title)],
        ];
        // the finger's press lies on the backdrop left of the box at the ruling's distances, unclamped: at the phone's width the
        // box's left edge is under 8px from the window's, so the 10px press lies just past the window's left edge (x under 0), which
        // the protocol accepts and Chromium delivers to the overlay; it closed the sheet at a6e7f1cfa and under the target-read form
        if (name === "chromium") roads.push(
          ["a finger pressed 6px left of the box's edge and lifted 6px inside it", (p) => touch([{ x: p.boxLeft - 6, y: p.input.y }, { x: p.boxLeft + 6, y: p.input.y }])],
          ["a finger pressed 10px left of the box's edge (past the window's left edge at the phone's width) and lifted 5px inside it", (p) => touch([{ x: p.boxLeft - 10, y: p.input.y }, { x: p.boxLeft + 5, y: p.input.y }])],
        );
        for (const [what, road] of roads) {
          await t.test(`at ${h}: ${what}`, async () => {
            await ready();
            const p = await points();
            await road(p);
            const st = await sheetState();
            assert.equal(st.up, true, `at ${h}, ${what}: the sheet stands (${JSON.stringify(p)}); at the head before this fix it closed with the answer`);
            assert.equal(st.value, TYPED, `at ${h}, ${what}: the answer is intact`);
            assert.equal(st.posted, 0, `at ${h}, ${what}: nothing was posted`);
          });
        }
        const taps: Array<[string, (p: Awaited<ReturnType<typeof points>>) => Promise<void>]> = [["a mouse tap on the backdrop", (p) => mouseDrag(p.back, p.back)]];
        if (name === "chromium") taps.push(["a finger's tap on the backdrop", (p) => touch([p.back])]);
        for (const [what, tap] of taps) {
          await t.test(`at ${h}: ${what} still dismisses`, async () => {
            await ready();
            const p = await points();
            await tap(p);
            const st = await sheetState();
            assert.equal(st.up, false, `at ${h}, ${what}: pressed and released on the backdrop, it dismisses (${JSON.stringify(p)}); what a dismiss does with the text is the filed discard item's`);
            assert.equal(st.posted, 0, `at ${h}, ${what}: a dismiss posts nothing`);
          });
        }
      }
      assert.deepEqual(errors, [], "no script error in the frame");
    } finally { await browser.close(); }
  });

  // THE WORST CASE, as its own test (the maintainer's round 2 ruling, B-i: the sheet guarantees Send inside the box's clip at
  // every geometry the rulings name and at the worst-case content, in both panes and three engines, measured by a click at
  // Send's centre that posts one answer with the typed text). With the keyboard up the box is capped at the visible height and
  // only the detail yields, down to two of its lines; the answer box keeps three rows, the ask keeps all its lines and the pane's
  // chips are rows of their own, so where those floors pass the cap the box scrolls, and at a6e7f1cfa the focus left the scroll
  // at the answer box with the buttons partly or wholly past the clip: clipped content is not hit-testable, so a finger at Send's
  // centre landed on the backdrop and the sheet closed with the answer. The actions row is now kept in view at the box's bottom
  // (styles.css #ut-reply-prompt .confirm-actions) and grow keeps the answer box clear of it. Driven at 390 and 320 wide, with the
  // keyboard up at 230, 300, 420, 480 and 508 and in the phone's order (opened at rest at 732, the keyboard then raised) at 420,
  // 480 and 508, on four asks at the cap, each with both chips and the linked forty-one-line detail: the 250-character fixture, a
  // 300-character ask, a multi-line ask at the cap (the tallest legal ask) and a 300-character unbreakable token; and on the
  // multi-line ask, the grip pulled 150px down with the keyboard up at each height, Send clicked after it. Per cell: Send wholly
  // inside the box's clip (its padding box) and the frame, a finger at its centre reaches it, and a click there posts exactly one
  // answer, the typed text, and closes the sheet by the send; the kept row's computed background is the box's own colour and not
  // transparent (the row is opaque, so what it covers at the box's bottom is hidden rather than seen through it and mis-tapped);
  // for typed answers also the answer box at three rows and the line being typed inside the clip and not under the kept row
  // (after the drag the dragged box's lower part lies below the clip, and Send, in the kept row, still sends). Each group of
  // cells is its own subtest, and its message names every failing cell
  test(`in ${name}: THE WORST CASE with the keyboard up (390 and 320 wide, 230 to 508, four asks at the cap with both chips, opened with the keyboard up, in the phone's order, and after a grip drag): Send is inside the box's clip and a click at its centre sends the typed answer`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension, and the browser legs need it; none of CI's browser-backed steps runs this leg, and the served leg tests/test_reply_sheet_served.py clicks Send in the worst case in CI's Browser-backed served-page tests (pytest) step"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box, and this leg needs it; none of CI's browser-backed steps runs this leg, and the served leg tests/test_reply_sheet_served.py is the guard where this skips (CI's Browser-backed served-page tests (pytest) step runs it in chromium): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { setWidth, sendCell, errors } = await boot(browser, name);
      const asks: Array<[string, string]> = [["t2", "the 250-character fixture"], ["t5", "a 300-character ask"], ["t6", "a multi-line ask at the cap"], ["t7", "a 300-character unbreakable token"]];
      const groups: Array<[string, string, "up" | "order" | "drag", number[]]> = [];
      for (const [todo, what] of asks) { groups.push([todo, what, "up", [230, 300, 420, 480, 508]]); groups.push([todo, what, "order", [420, 480, 508]]); }
      groups.push(["t6", "a multi-line ask at the cap", "drag", [230, 300, 420, 480, 508]]);
      for (const [todo, what, how, heights] of groups) {
        const label = how === "up" ? "opened with the keyboard up" : how === "order" ? "in the phone's order (opened at rest at 732, the keyboard then raised)" : "the grip pulled 150px down with the keyboard up, then Send";
        await t.test(`${what}, ${label}, at ${heights.join(", ")}`, async (st) => {
          const fails: string[] = [], roads: string[] = [];
          for (const w of [PHONE_W, 320]) {
            await setWidth(w);
            for (const h of heights) {
              const c = await sendCell(todo, h, how);
              const cell = `${w}x${h}`;
              if (c.road) roads.push(`${cell} ${c.road}`);
              const m = c.m;
              if (!m) { fails.push(`${cell}: no sheet to read`); continue; }
              const why: string[] = [];
              if (!(m.frameW === w && m.frameH === h)) why.push(`the window is ${m.frameW}x${m.frameH}`);
              if (!(m.sendTop >= m.clipTop - 0.5 && m.sendBottom <= m.clipBottom + 0.5)) why.push(`Send ${m.sendTop.toFixed(1)}..${m.sendBottom.toFixed(1)} is not inside the box's clip ${m.clipTop.toFixed(1)}..${m.clipBottom.toFixed(1)}`);
              if (!(m.sendTop >= -0.5 && m.sendBottom <= m.frameH + 0.5)) why.push(`Send is not inside the ${m.frameH}px window`);
              if (m.hit !== "target") why.push(`a finger at Send's centre reaches ${m.hit}`);
              if (!(m.rowBg === m.boxBg && alphaOf(m.rowBg) > 0)) why.push(`the kept actions row's background is ${m.rowBg}, not the box's ${m.boxBg} (the row must be painted in the box's own colour, not transparent, so what scrolls under it is hidden rather than seen through it)`);
              if (!(c.posted.length === 1 && c.posted[0] === c.typed && !c.up)) why.push(c.posted.length === 0 ? (c.up ? "the click posted nothing and the sheet stood" : "the click CLOSED the sheet and posted nothing: the answer was discarded") : `the click posted ${c.posted.length} answer(s)${c.posted[0] !== c.typed ? ", not the typed text" : ""}${c.up ? ", and the sheet stood" : ""}`);
              if (how !== "drag") {
                if (!(m.inputH >= m.floorH - 1)) why.push(`the answer box is ${m.inputH}px, under its three rows (${m.floorH}px)`);
                if (!(m.rowBottom <= m.actionsTop + 0.5)) why.push(`the line being typed (${m.rowTop.toFixed(1)}..${m.rowBottom.toFixed(1)}) is under the actions row (its top at ${m.actionsTop.toFixed(1)})`);
                if (!(m.rowTop >= m.clipTop - 0.5 && m.rowBottom <= m.clipBottom + 0.5)) why.push(`the line being typed (${m.rowTop.toFixed(1)}..${m.rowBottom.toFixed(1)}) is outside the box's clip`);
              }
              if (why.length) fails.push(`${cell}: ${why.join("; ")} (box over its cap by ${m.over}px, scrolled ${m.boxScrollTop}px, answer box ${m.inputH}px, inline height ${m.inputStyleH || "none"})`);
            }
          }
          if (roads.length) st.diagnostic(`${name}: the drag's road per cell: ${roads.join("; ")}`);
          assert.deepEqual(fails, [], `${what}, ${label}: at every cell Send is inside the box's clip and under a finger, and a click at its centre posts the typed answer once and closes the sheet (at a6e7f1cfa Send lay past the clip in states like these, and a click at its centre closed the sheet with the answer)`);
        });
      }
      assert.deepEqual(errors, [], "no script error in the frame");
    } finally { await browser.close(); }
  });
}
