import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, frames, requireCjs, UI, EXT, ORIGIN } from "./real-viewer-leg";

// The Sessions pane's row menu (the user 2026-09-16): Rename and Delete on the tab strip's own roads, through the shared
// builder. These pins hold the wiring's shape; the served lab (tests/test_sessions_menu_served.py) drives it.
//
// THE MENU'S CLOSE AND THE KEYBOARD (the catch-up fold's review, round 1, ui-1): the row menu's onClose refocused the
// row's head on EVERY close, the window's blur included, and the blur is how the menu closes when the person clicks into
// another pane without picking. Reproduced in Firefox with the served shell's frame arrangement (the chat and Sessions
// panes as sibling iframes): right-click a row, click the chat composer, and the composer LOSES the keyboard; the letters
// typed next land on the head, where Space or Enter opens that session in place of typing. Chromium keeps the composer
// through the frame switch (a frame-focus re-entrancy guard), so there the residue is a stale activeElement, the head, in
// the unfocused Sessions frame. The fix guards the return as the builder does: a close that followed the focus out of
// the document (document.hasFocus() false) moves nothing; Escape, Tab and a pick still hand the focus back to the head,
// by sid, so the return survives a push that rebuilt the list under the open menu (the builder's own return only
// refocuses a still-connected opener, which is why onClose stays). Two browser legs below run the REAL fleet.ts bundle
// in that frame arrangement: the Chromium one is the fails-before case (the residue: after the menu closed on a click
// into the chat frame, the Sessions frame's activeElement is the head as written and the body under the guard), with
// the Escape return and the rebuild-then-Escape return beside it; the Firefox one pins the user-visible loss itself and
// skips LOUDLY where that engine is not installed (CI installs no browsers). Synthetic values only: the notes-api world,
// the placeholder sid.
const PANE = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "fleet.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");

test("a right-click on a session's head, or the menu key on the focused head, opens the shared menu; the goal rows keep their clicks", () => {
  assert.match(PANE, /import \{ openContextMenu, openConfirmBox \} from "\.\/ctx-menu";/);
  assert.match(PANE, /list\.addEventListener\("contextmenu", \(e\) => \{\s*\n\s*const head = \(e\.target as Element\)\.closest\?\.\("\.fl-head"\) as HTMLElement \| null;\s*\n\s*if \(!head \|\| !head\.dataset\.sid\) return;/);
  assert.match(PANE, /if \(e\.key === "ContextMenu" \|\| \(e\.key === "F10" && e\.shiftKey\)\) \{/, "the row's menu key and Shift+F10");
  assert.match(PANE, /showSessionMenu\(r\.left \+ 12, r\.bottom, head\.dataset\.sid, true\);/, "a keyboard opening anchors to the row and focuses the first item; the menu is keyed by sid, never the node");
  assert.match(PANE, /showSessionMenu\(e\.clientX, e\.clientY, head\.dataset\.sid, false\);/);
  assert.match(PANE, /function headOf\(sid: string\): HTMLElement \| null \{\s*\n\s*return document\.querySelector\('#fleet-list \.fl-head\[data-sid="' \+ CSS\.escape\(sid\) \+ '"\]'\) as HTMLElement \| null;/,
    "every pick resolves the row's head by sid at pick time (round two, high: a push between the open and the pick rebuilt the list and the pick worked on a detached row, latching the render hold)");
  assert.equal((PANE.match(/head\.tabIndex = 0; head\.setAttribute\("role", "button"\);/g) || []).length, 2, "both head shapes (a tree's, a provisional-only) are focusable");
});

test("Rename edits in place with the strip's rules and posts the strip's message; render waits while the input is open", () => {
  const fn = PANE.slice(PANE.indexOf("function startRowRename("), PANE.indexOf("function confirmEndSession("));
  assert.match(fn, /const head = headOf\(sid\);/, "the row as it stands now");
  assert.match(fn, /if \(!head \|\| !nm \|\| renameHold\) return;/, "a row that is gone: nothing to edit, nothing held");
  assert.match(fn, /const p = hostPrefix\(full, sid\);[^\n]*\n\s*const base = p \? p\.rest : full;/, "a federated row's name is edited bare (round two, medium: the host prefix was seeded and posted)");
  assert.match(fn, /const fixed = p \? document\.createElement\("span"\) : null;[^\n]*\n\s*if \(fixed\) \{ fixed\.className = "host-prefix"; fixed\.textContent = p!\.host; \}/,
    "the host prefix stays beside the input as the row renders it (round three, low: the input replaced the whole name span and the prefix vanished while editing)");
  assert.match(fn, /nm\.replaceWith\(input\);\s*\n\s*if \(fixed\) input\.before\(fixed\);\s*\n\s*if \(!input\.isConnected\) return;[^\n]*\n\s*renameHold = true;/, "the render hold is set only for an input in the document");
  assert.match(fn, /if \(input\.isConnected\) input\.replaceWith\(nm\);\s*\n\s*fixed\?\.remove\(\);\s*\n\s*if \(hadFocus && row\.isConnected\) row\.focus\(\{ preventScroll: true \}\);/,
    "the edit's end removes the fixed prefix with the input; a keyboard end hands the focus back to the row");
  assert.match(fn, /input\.className = "fl-rename";/);
  assert.match(fn, /if \(e\.key === "Enter"\) \{ e\.preventDefault\(\); finish\(true\); \}\s*\n\s*else if \(e\.key === "Escape"\) \{ e\.preventDefault\(\); finish\(false\); \}/);
  assert.match(fn, /input\.addEventListener\("blur", \(\) => finish\(true\)\);/);
  assert.match(fn, /if \(commit && v && v !== base\) vscodeApi\?\.postMessage\(\{ type: "renameSession", id: sid, name: v \}\);/, "the tab menu's exact wire message, only for a changed non-empty name");
  assert.doesNotMatch(fn, /nm\.textContent = v|textContent = input\.value/, "nothing renamed locally ahead of the kernel");
  assert.match(PANE, /if \(renameHold\) \{ renameDirty = true; return; \}/, "a push mid-edit waits");
  assert.match(fn, /renameHold = false;\s*\n\s*if \(renameDirty\) \{ renameDirty = false; render\(\); \}/, "…and paints when the edit ends");
});

test("Delete is the strip's close-button road: the End confirm with the open goals named, then endSession and closeTab in that order; Cancel does nothing", () => {
  const fn = PANE.slice(PANE.indexOf("function confirmEndSession("), PANE.indexOf("// Fleet-list clicks are DELEGATED"));
  assert.match(fn, /const titles = openTopTitles\(\(sessionRow\(sid\)\?\.ledger\?\.tree \|\| \[\]\) as any\);/, "the live ledger at click time, as the strip reads it (round two, low d)");
  assert.match(PANE, /import \{ openTopTitles, endConfirmDetail, RENAME_SUBLINE, END_SESSION_STANDING \} from "\.\/clear-confirm";/, "the strip's own detail builder and its two sentences");
  assert.match(fn, /openConfirmBox\("End \\u201c" \+ name \+ "\\u201d\?",/, "the strip's title, through the shared confirm box");
  assert.match(fn, /endConfirmDetail\(titles, END_SESSION_STANDING\)/, "the strip's standing sentence, one copy (clear-confirm.ts)");
  assert.match(fn, /\[\{ label: "End session", value: "end", danger: true \}, \{ label: "Cancel", value: "" \}\]/);
  assert.match(fn, /if \(v !== "end"\) return;[^\n]*\n\s*vscodeApi\?\.postMessage\(\{ type: "endSession", id: sid \}\);[^\n]*\n\s*vscodeApi\?\.postMessage\(\{ type: "closeTab", id: sid \}\);/);
  assert.doesNotMatch(fn, /sec\.remove\(\)|head\.remove\(\)|render\(\)/, "the row leaves on the kernel's push, never locally ahead of it");
});

test("the menu's rows: Rename first, Delete second and marked danger; the danger dress is a token rule in the reference sheet", () => {
  const fn = PANE.slice(PANE.indexOf("function showSessionMenu("), PANE.indexOf("function startRowRename("));
  assert.match(fn, /\{ label: "Rename", sub: RENAME_SUBLINE, pick: \(\) => startRowRename\(sid\) \},\s*\n\s*\{ label: "Delete", sub: "ends the session; its history stays on disk", danger: true, pick: \(\) => confirmEndSession\(sid\) \},/,
    "both picks carry the sid alone");
  assert.match(fn, /onClose: \(\) => \{ if \(!document\.hasFocus\(\)\) return; const h = headOf\(sid\); if \(h\) h\.focus\(\{ preventScroll: true \}\); \}/,
    "focus returns to the row's head when the menu closes (round two, low a), unless the close followed the focus out of the document: the window's blur, a click into another pane (the fold review's ui-1: the composer lost the keyboard to the head in Firefox)");
  assert.doesNotMatch(fn, /onClose: \(\) => \{ const h = headOf\(sid\);/, "the unguarded return is gone");
  assert.match(PANE, /document\.addEventListener\("focusin", \(e\) => \{[^\n]*\n\s*focusedHead = \(e\.target as Element\)\.closest\?\.\("\.fl-head"\) as HTMLElement \| null;/,
    "the focused head is remembered as the node, never its sid alone");
  assert.match(PANE, /import \{ openTopTitles, endConfirmDetail, RENAME_SUBLINE, END_SESSION_STANDING \} from "\.\/clear-confirm";/);
  assert.match(CSS, /\.ctx-item-danger \.ctx-item-label \{ color: var\(--vscode-errorForeground, #f48771\); \}/, "a var() with the confirm button's fallback, never a bare hex");
});

test("a rebuild restores the focus only when it removed the head that held it and the pane has the focus; a push never pulls the focus into the pane", () => {
  // round three, high: the round-two restore (focusedHeadSid set, activeElement fallen to body) fired on EVERY push once a head had been focused, so a
  // head left for a goal row and then the chat composer took the window's focus back on the next push and each space pressed the head (openSession)
  const start = PANE.indexOf("function render() {");
  const render = PANE.slice(start, PANE.indexOf("\nfunction ", start + 1));   // render() up to the next top-level function
  assert.match(render, /const held = focusedHead;[^\n]*\n\s*const heldActive = !!held && held\.isConnected && held\.contains\(document\.activeElement\);[^\n]*\n\s*rebuilding = true;\s*\n\s*list\.replaceChildren\(\);\s*\n\s*rebuilding = false;/,
    "the focused node and whether it holds the focus are read before the rebuild, which is bracketed so its focusout is not read as the user leaving");
  assert.match(render, /if \(held && !held\.isConnected\) \{\s*\n\s*const next = heldActive && document\.hasFocus\(\) && held\.dataset\.sid \? headOf\(held\.dataset\.sid\) : null;\s*\n\s*focusedHead = next;\s*\n\s*next\?\.focus\(\{ preventScroll: true \}\);\s*\n\s*\}/,
    "restore only when THIS render removed the node, it held the focus, and the document has the focus; the removed node is dropped either way");
  assert.doesNotMatch(render, /document\.activeElement === document\.body/, "no proxy for the event: the body holding the focus says nothing about how it got there");
  assert.match(PANE, /list\.addEventListener\("focusout", \(e\) => \{[^\n]*\n\s*if \(rebuilding\) return;[^\n]*\n\s*const to = e\.relatedTarget as Node \| null;\s*\n\s*if \(!to \|\| !list\.contains\(to\)\) focusedHead = null;/,
    "focus leaving the list clears the remembered head, except the focusout the rebuild's own removal fires");
  assert.match(PANE, /let focusedHead: HTMLElement \| null = null;/);
  assert.match(PANE, /let rebuilding = false;/);
  assert.equal((PANE.match(/focusedHeadSid/g) || []).length, 0, "the sid-keyed record is gone");
});

// ── the browser legs: the real fleet.ts bundle in the served shell's frame arrangement ─────────────────────────────────
// The kernel's landing page hosts the chat and the Sessions panes as sibling same-origin iframes (f-chat and f-fleet). The
// stand-in below is that arrangement: a chat frame holding a textarea composer, and a Sessions frame that is the kernel's
// outline page stood in (the chat's sheet and fleet-pane.css, the page's own divs, the shim's acquireVsCodeApi recording
// every post) running fleet.ts bundled from this tree as the webview build bundles it, fed one feed frame the way the shim
// dispatches a kernel frame. No fake DOM: a real engine reads the focus.
const web = (f: string) => fs.readFileSync(path.join(UI, f), "utf8").replace('@import "katex/dist/katex.min.css";', "");
const SID = "11111111-2222-3333-4444-555555555555";
const HEAD = '.fl-head[data-sid="' + SID + '"]';
const MENU = ".ctx-menu.fl-sess-menu";
const COMPOSER = "TEXTAREA#composer-input";

let paneBundle: string | null = null;
/** fleet.ts as the webview build bundles it (esbuild.js's fleet.ts entry), in memory. */
function bundlePane(): string {
  if (paneBundle) return paneBundle;
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, "fleet.ts")], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  assert.equal(r.outputFiles.length, 1, "the fleet entry bundles to one output (fleet.ts imports no sheet; fleet-pane.css is the build's own entry)");
  paneBundle = r.outputFiles[0].text as string;
  return paneBundle;
}
/** The Sessions page: the kernel's outline page stood in, the shim's acquireVsCodeApi recording every post, then the real bundle. */
function panePage(): string {
  return `<!DOCTYPE html><html><head><meta charset=utf-8><style>${web("styles.css")}\n${web("fleet-pane.css")}</style></head>
<body><div id="fleet-search-bar"><div id="fleet-search-wrap"><input id="fleet-search" type="search" autocomplete="off" placeholder="Search"><button id="fleet-search-clear" type="button" hidden>x</button></div></div>
<div id="fleet-list"></div><div id="fleet-foot"></div><script>
window.__posted = [];
window.acquireVsCodeApi = function () { return { postMessage: function (m) { window.__posted.push(m); } }; };
</script><script>${bundlePane()}</script></body></html>`;
}
const CHAT = '<!DOCTYPE html><html><body style="margin:8px"><textarea id="composer-input" style="width:260px;height:80px"></textarea><p id="plain">chat pane stand-in</p></body></html>';
const SHELL = `<!DOCTYPE html><html><body style="margin:0"><div style="height:20px">shell stand-in</div><iframe id="f-chat" src="${ORIGIN}/chat" style="width:340px;height:560px"></iframe><iframe id="f-fleet" src="${ORIGIN}/fleet" style="width:620px;height:560px"></iframe></body></html>`;

/** One feed frame as the kernel's push carries it: the session `name` with one open top inside the pane's age window. */
function feedFrame(name: string): Record<string, unknown> {
  const now = Math.floor(Date.now() / 1000);
  return { type: "feed", now, nowAt: now * 1000, sessions: [], asks: [], ledgers: [{ sid: SID, name, color: { bg: "#3a86ff", fg: "#ffffff" }, status: { state: "ready" },
    ledger: { current: null, archivedTops: [], tree: [{ id: "g1", depth: 0, done: false, text: "Wire the notes-api health route", t: now - 60, mt: now - 60 }] } }] };
}
/** The shim's delivery of a kernel frame to the pane: a message event dispatched on the pane's window. */
const deliver = (fb: any, m: Record<string, unknown>): Promise<void> => fb.evaluate((f: Record<string, unknown>) => { window.dispatchEvent(new MessageEvent("message", { data: f })); }, m);

type Mounted = { page: any; fa: any; fb: any; errors: string[] };
/** The shell stand-in with the chat frame and the Sessions frame loaded, the pane fed one frame and the row painted. */
async function mount(browser: any): Promise<Mounted> {
  const page = await browser.newPage({ viewport: { width: 1000, height: 600 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const paneHtml = panePage();
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => {
    const p = new URL(route.request().url()).pathname;
    if (p === "/") return route.fulfill({ status: 200, contentType: "text/html", body: SHELL });
    if (p === "/chat") return route.fulfill({ status: 200, contentType: "text/html", body: CHAT });
    if (p === "/fleet") return route.fulfill({ status: 200, contentType: "text/html", body: paneHtml });
    return route.fulfill({ status: 404, contentType: "text/plain", body: "" });
  });
  await page.goto(ORIGIN + "/");
  const fa = page.frames().find((f: any) => f.url() === ORIGIN + "/chat"), fb = page.frames().find((f: any) => f.url() === ORIGIN + "/fleet");
  assert.ok(fa && fb, "both iframes loaded");
  await fb.waitForFunction(() => !!document.getElementById("fleet-list") && Array.isArray((window as any).__posted), null, { timeout: 10000 });
  await deliver(fb, feedFrame("web"));
  await fb.waitForFunction((sel: string) => !!document.querySelector(sel), HEAD, { timeout: 10000 });
  await frames(fb, 2);
  return { page, fa, fb, errors };
}
type Holder = { active: string; hasFocus: boolean };
/** A frame's active element (tag, id, classes) and whether its document holds the page's focus. */
const holder = (frame: any): Promise<Holder> => frame.evaluate(() => { const a = document.activeElement as HTMLElement | null; return { active: a ? a.tagName + (a.id ? "#" + a.id : "") + (a.className ? "." + String(a.className).split(/\s+/).filter(Boolean).join(".") : "") : "none", hasFocus: document.hasFocus() }; });
/** The sid of the session head holding the Sessions document's focus, or null. */
const focusedHead = (fb: any): Promise<string | null> => fb.evaluate(() => { const a = document.activeElement as HTMLElement | null; return a && a.classList.contains("fl-head") ? (a.dataset.sid || null) : null; });
const menuOpen = (fb: any): Promise<boolean> => fb.evaluate((sel: string) => !!document.querySelector(sel), MENU);
const composer = (fa: any): Promise<string> => fa.evaluate(() => (document.getElementById("composer-input") as HTMLTextAreaElement).value);
/** The pane's posts of one type (the shim's record). */
const postedOf = (fb: any, type: string): Promise<unknown[]> => fb.evaluate((t: string) => (window as any).__posted.filter((m: any) => m && m.type === t), type);
const waitMenu = (fb: any, open: boolean): Promise<unknown> => fb.waitForFunction(([sel, want]: [string, boolean]) => !!document.querySelector(sel) === want, [MENU, open], { timeout: 5000 });
/** The composer typed in, the head right-clicked (the menu up, the Sessions frame holding the page's focus), then the click back into
 *  the composer, which closes the menu through the Sessions window's blur: the scene both engines' legs read after. */
async function menuThenClickComposer(page: any, fa: any, fb: any): Promise<void> {
  await fa.click("#composer-input"); await page.keyboard.type("abc");
  assert.equal((await holder(fa)).active, COMPOSER, "the composer holds the keyboard before the menu");
  await fb.click(HEAD, { button: "right" });
  await waitMenu(fb, true);
  assert.equal((await holder(fb)).hasFocus, true, "the right-click gave the Sessions frame the page's focus, the menu up");
  await fa.click("#composer-input");   // back to typing without picking: the Sessions window's blur closes the menu
  await waitMenu(fb, false);
}

test("in a browser, the real Sessions bundle beside a chat frame: a click into the composer closes the open row menu and moves NOTHING in the Sessions frame (its activeElement is the body, not the head: the Chromium residue of the pull, the fails-before read), the composer keeps the keyboard and takes the next letters and no session opens; Escape still returns the focus to the head, and after a push rebuilt the list under the open menu Escape lands on the same session's new head (why onClose stays)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, fa, fb, errors } = await mount(browser);
    // the pull: the menu closed by the blur, the head refocused (as written) or left alone (guarded)
    await menuThenClickComposer(page, fa, fb);
    const b = await holder(fb), a = await holder(fa);
    assert.equal(await focusedHead(fb), null, "RESIDUE: after the menu closed on the click into the chat frame, the Sessions frame's activeElement is not the head (read " + b.active + "): the close followed the focus out of the pane and moved nothing");
    assert.equal(b.active, "BODY", "the Sessions document's focus fell to its body with the menu's removal and stayed there");
    assert.equal(b.hasFocus, false, "the Sessions document does not hold the page's focus");
    assert.equal(a.active, COMPOSER, "the composer holds the keyboard after the close");
    assert.equal(a.hasFocus, true, "the chat document holds the page's focus");
    await page.keyboard.type(" hello");
    assert.equal(await composer(fa), "abc hello", "the letters typed after the close reach the composer");
    assert.deepEqual(await postedOf(fb, "openSession"), [], "no key pressed the head: no session was opened");
    // the return the guard keeps: Escape hands the focus back to the head (the menu opened from the keyboard, as road 4 does)
    await fb.evaluate((sel: string) => { (document.querySelector(sel) as HTMLElement).focus(); }, HEAD);
    await fb.locator(HEAD).press("Shift+F10");
    await waitMenu(fb, true);
    assert.equal(await fb.evaluate((sel: string) => { const m = document.querySelector(sel); return !!m && m.contains(document.activeElement) && (document.activeElement as HTMLElement).classList.contains("ctx-item"); }, MENU), true, "a keyboard opening focuses the first row");
    await page.keyboard.press("Escape");
    await waitMenu(fb, false);
    assert.equal(await focusedHead(fb), SID, "Escape: the focus returns to the row's head");
    assert.equal((await holder(fb)).hasFocus, true, "the Sessions document holds the page's focus after Escape");
    // a push rebuilds the list while the menu is open: the opener is detached, the builder's own return does nothing, and the sid-keyed onClose lands on the new head
    await fb.evaluate((sel: string) => { (document.querySelector(sel) as HTMLElement).dataset.probe = "old"; }, HEAD);
    await fb.click(HEAD, { button: "right" });
    await waitMenu(fb, true);
    await deliver(fb, feedFrame("web-two"));
    await fb.waitForFunction((sel: string) => { const n = document.querySelector(sel + " .fl-name"); return !!n && n.textContent === "web-two"; }, HEAD, { timeout: 5000 });
    assert.equal(await fb.evaluate((sel: string) => (document.querySelector(sel) as HTMLElement).dataset.probe, HEAD), undefined, "the push rebuilt the row: the head under the open menu is a new node");
    assert.equal(await menuOpen(fb), true, "the menu is still up over the rebuilt list");
    await page.keyboard.press("Escape");
    await waitMenu(fb, false);
    assert.equal(await focusedHead(fb), SID, "Escape after the rebuild: the same session's NEW head holds the focus (dropping onClose would have left it on the body)");
    assert.equal(await fb.evaluate((sel: string) => (document.querySelector(sel + " .fl-name") as HTMLElement).textContent, HEAD), "web-two", "the head that holds the focus is the rebuilt one");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }
/** Headless Firefox, the engine where the pull reproduced as the composer losing the keyboard, or a LOUD skip (CI installs no browsers). */
async function inFirefox(t: any, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.firefox.launch(); }
  catch (e) { t.skip("no playwright Firefox on this box; this leg needs that engine (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

test("in Firefox, the same scene: after the click into the composer closed the row menu, the composer keeps the keyboard and takes the next letters, the head holds no focus and no session opens (as written, the head took the focus back and the letters landed on it, where Space or Enter opens the session)", { timeout: 240000 }, async (t) => {
  await inFirefox(t, async (browser) => {
    const { page, fa, fb, errors } = await mount(browser);
    await menuThenClickComposer(page, fa, fb);
    const a = await holder(fa);
    assert.equal(a.active, COMPOSER, "FIREFOX: the composer holds the keyboard after the close (read " + a.active + "; as written the head took it back)");
    assert.equal(await focusedHead(fb), null, "FIREFOX: no head holds the Sessions document's focus after the close (read " + (await holder(fb)).active + ")");
    await page.keyboard.type(" hello");
    assert.equal(await composer(fa), "abc hello", "FIREFOX: the letters typed after the close reach the composer, not the head");
    assert.deepEqual(await postedOf(fb, "openSession"), [], "FIREFOX: no key pressed the head: no session was opened");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});
