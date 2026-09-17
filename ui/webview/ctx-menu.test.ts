import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { placeMenu, menuCard, addMenuItem, showMenuCard, closeContextMenu, contextMenuOpen } from "./ctx-menu";
import { nodeFactory, defineHidden, describeNode } from "../test-dom-shim";

// The shared context menu builder (the Sessions pane's Rename and Delete, the user 2026-09-16): the pure placement rule is
// executed here; the DOM rules (the chat's classes through the theme tokens, dismissal, keyboard reach, the confirm box in the
// chat's classes) are pinned in the source, and the served lab drives them on the real page. The focus at the close is
// executed too, on the shim's nodes with the real showMenuCard and render.ts's close callbacks lifted from the source: the
// tab menu's puts the focus on the active tab when a push rebuilt the strip under the open menu (the fold's review
// 2026-09-17, correctness-1) and takes it WITHOUT scrolling the strip's bar, so a press on another tab that dismisses the
// menu keeps that tab under the pointer and its click lands (review round 2, tests-1 and ui-1); the selection menu's moves
// none.
const SRC = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "ctx-menu.ts"), "utf8");
const requireCjs = createRequire(__filename);
const readWebview = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");

test("the card opens right and below the pointer when it fits, flips left or up when it does not, and never leaves the viewport", () => {
  assert.deepEqual(placeMenu(100, 100, 150, 80, 1000, 800), { left: 100, top: 100 });
  assert.deepEqual(placeMenu(950, 100, 150, 80, 1000, 800), { left: 800, top: 100 }, "no room to the right: to the left of the pointer");
  assert.deepEqual(placeMenu(100, 780, 150, 80, 1000, 800), { left: 100, top: 700 }, "no room below: above the pointer");
  assert.deepEqual(placeMenu(2, 2, 150, 80, 1000, 800), { left: 4, top: 4 }, "never past the top-left margin");
  assert.deepEqual(placeMenu(990, 790, 150, 80, 1000, 800), { left: 840, top: 710 }, "both flips, clamped inside");
  assert.deepEqual(placeMenu(20, 20, 300, 200, 200, 100), { left: 4, top: 4 }, "a card larger than the viewport sits at the margin");
});

test("the menu wears the chat's classes and roles, and its rows carry the label, the sub-line and the danger mark", () => {
  assert.match(SRC, /menu\.className = "ctx-menu" \+ \(opts\.className \? " " \+ opts\.className : ""\);/);
  assert.match(SRC, /menu\.setAttribute\("role", "menu"\);/);
  assert.match(SRC, /row\.className = "ctx-item ctx-item-toggle" \+ \(it\.danger \? " ctx-item-danger" : ""\) \+ \(it\.className \? " " \+ it\.className : ""\);/);
  assert.match(SRC, /row\.setAttribute\("role", "menuitem"\);/);
  assert.match(SRC, /label\.className = "ctx-item-label"; label\.textContent = it\.label;/);
  assert.match(SRC, /sub\.className = "ctx-item-sub"; sub\.textContent = it\.sub;/);
  assert.doesNotMatch(SRC, /#[0-9a-fA-F]{6}|rgba?\(/, "no colour in the builder: the sheet's tokens dress it");
});

test("dismissal is a press outside, Escape, any scroll or the window's blur; every listener is removed on close", () => {
  assert.match(SRC, /document\.addEventListener\("pointerdown", onDown, true\);\s*\n\s*document\.addEventListener\("keydown", onKey, true\);\s*\n\s*document\.addEventListener\("scroll", onScroll, true\);\s*\n\s*window\.addEventListener\("blur", onBlur\);/);
  assert.match(SRC, /document\.removeEventListener\("pointerdown", onDown, true\);\s*\n\s*document\.removeEventListener\("keydown", onKey, true\);\s*\n\s*document\.removeEventListener\("scroll", onScroll, true\);\s*\n\s*window\.removeEventListener\("blur", onBlur\);/);
  assert.match(SRC, /const onDown = \(e: Event\) => \{ if \(!menu\.contains\(e\.target as Node\)\) closeContextMenu\(\); \};/, "a press inside the card is not a dismissal");
});

test("keyboard reach: arrows and Home/End move between rows, Enter or Space picks, Escape closes; a keyboard opening focuses the first row", () => {
  assert.match(SRC, /if \(ev\.key === "Escape"\) \{ ev\.preventDefault\(\); ev\.stopPropagation\(\); closeContextMenu\(\); return; \}/);
  assert.match(SRC, /else if \(ev\.key === "ArrowDown"\) \{ ev\.preventDefault\(\); ev\.stopPropagation\(\); move\(list, at, 1\); \}/);
  assert.match(SRC, /else if \(ev\.key === "ArrowUp"\) \{ ev\.preventDefault\(\); ev\.stopPropagation\(\); move\(list, at < 0 \? list\.length : at, -1\); \}/);
  assert.match(SRC, /else if \(\(ev\.key === "Enter" \|\| ev\.key === " "\) && at >= 0\) \{ ev\.preventDefault\(\); ev\.stopPropagation\(\); list\[at\]\.click\(\); \}/);
  assert.match(SRC, /if \(opts\.viaKeyboard && list\.length\) list\[0\]\.focus\(\); else menu\.focus\(\);/);
  assert.match(SRC, /if \(ev\.key === "Tab"\) \{ ev\.preventDefault\(\); ev\.stopPropagation\(\); closeContextMenu\(\); \}/, "Tab closes the card (round two, low b)");
  assert.match(SRC, /menu\.addEventListener\("focusout", \(e\) => \{ const to = e\.relatedTarget as Node \| null; if \(to && !menu\.contains\(to\)\) closeContextMenu\(\); \}\);/, "focus leaving the card closes it");
});

test("the confirm box is the chat's dialog in its classes; Cancel, Escape and the backdrop all answer with the empty value once", () => {
  assert.match(SRC, /overlay\.className = "picker-overlay confirm-overlay"; overlay\.id = "confirm";/);
  assert.match(SRC, /box\.className = "picker-box confirm-box";/);
  assert.match(SRC, /h\.className = "confirm-title"; h\.textContent = title;/);
  assert.match(SRC, /d\.className = "confirm-detail"; d\.textContent = detail;/);
  assert.match(SRC, /btn\.className = "picker-action confirm-btn" \+ \(b\.danger \? " danger" : ""\);/);
  assert.match(SRC, /if \(settled\) return;\s*\n\s*settled = true;\s*\n\s*if \(confirmFinish === finish\) confirmFinish = null;/, "one answer per box");
  assert.match(SRC, /if \(confirmFinish\) confirmFinish\(""\);   \/\/ a box already open answers Cancel and goes, its Escape listener with it/, "a replacing box settles the open one first (round two, low c)");
  assert.match(SRC, /overlay\.addEventListener\("click", \(e\) => \{ if \(e\.target === overlay\) finish\(""\); \}\);/);
  assert.match(SRC, /const onKey = \(e: KeyboardEvent\) => \{ if \(e\.key === "Escape"\) \{ e\.preventDefault\(\); e\.stopPropagation\(\); finish\(""\); \} \};/);
});

test("the tidy (v0.16.0): every menu opens through the builder; a caller with rows of its own builds the card, adds beside the standard rows and shows it", () => {
  assert.match(SRC, /export function menuCard\(opts: CtxMenuOpts = \{\}\): HTMLElement \{/);
  assert.match(SRC, /export function addMenuItem\(menu: HTMLElement, it: CtxItem\): HTMLElement \{/);
  assert.match(SRC, /export function addMenuSep\(menu: HTMLElement\): HTMLElement \{/);
  assert.match(SRC, /export function showMenuCard\(menu: HTMLElement, x: number, y: number, opts: CtxMenuOpts = \{\}\): HTMLElement \{/);
  assert.match(SRC, /if \(opts\.id\) menu\.id = opts\.id;/, "the file browser keeps its #fb-ctx");
  assert.match(SRC, /if \(it\.icon\) row\.appendChild\(it\.icon\);/, "the drawn icon before the body (the tab menu's toggles, the card menu's bell)");
  assert.match(SRC, /if \(typingIn\(ev\.target\)\) return;/, "a key inside a field the menu holds is the field's (the tags flyout's input)");
  assert.match(SRC, /if \(!c\.classList\.contains\("ctx-item"\)\) continue;/, "the card's own rows, never a flyout's");
  assert.match(SRC, /if \(opener && opener !== document\.body && opener\.isConnected && document\.hasFocus\(\)\s*\n\s*&& \(menu\.contains\(active\) \|\| active === document\.body \|\| active === null\)\) opener\.focus\(\{ preventScroll: true \}\);/,
    "the focus goes back to the opener only when the card held it and the document has the focus (the Sessions pane's round-three rule)");
  const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
  assert.match(read("render.ts"), /ctxMenuEl = showMenuCard\(menu, e\.clientX, e\.clientY, \{ onClose: onTabMenuClosed \}\);/, "the chat tab menu");
  assert.match(read("render.ts"), /ctxMenuEl = openContextMenu\(e\.clientX, e\.clientY, items, \{ onClose: onSelectionMenuClosed \}\);/, "the chat selection menu, on its own plain close callback (the tab menu's refocuses the active tab; see the close cases below)");
  assert.match(read("feed.ts"), /openContextMenu\(e\.clientX, e\.clientY, items\);/, "the feed card menu");
  assert.match(read("file-browse.ts"), /openContextMenu\(e\.clientX, e\.clientY, items, \{ id: "fb-ctx" \}\);/, "the file browser's row menu");
  for (const f of ["render.ts", "feed.ts", "file-browse.ts"]) assert.doesNotMatch(read(f), /el\("div", "ctx-menu"\)/, f + " builds no top-level card by hand");
  assert.doesNotMatch(read("render.ts"), /window\.addEventListener\("(mousedown|scroll)", \(e\) => \{ if \(ctxMenuEl/, "no dismissal listeners of the tab menu's own");
});

test("every key the menu consumes stops at the card: a surface under it never walks on the menu's arrows (round two)", () => {
  // the file browser's document-level handler walked its listing on the same ArrowDown that moved the menu's focus
  const keys = SRC.slice(SRC.indexOf('menu.addEventListener("keydown"'), SRC.indexOf("// the menu never becomes the row's click"));
  for (const k of ["Tab", "ArrowDown", "ArrowUp", "Home", "End"]) assert.match(keys, new RegExp('ev\\.key === "' + k + '"\\) \\{ ev\\.preventDefault\\(\\); ev\\.stopPropagation\\(\\);'), k + " stops");
  assert.doesNotMatch(keys, /preventDefault\(\); (?:move|list\[|closeContextMenu)/, "no consumed key without the stop");
  const browse = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-browse.ts"), "utf8");
  assert.match(browse, /if \(document\.getElementById\("fb-ctx"\) \|\| \(e\.key === "Escape" && e\.defaultPrevented\)\) return;/, "the browser yields every key to an open row menu, per its topmost-first comment");
});

// ── the focus at the close: render.ts's close callbacks on the real builder ──────────────────────────────────────────────
// closeContextMenu runs the teardown (the focus back to the opener when that node still stands and the card or the body
// holds it, then opts.onClose) BEFORE it removes the card, so at onClose the card is still on the page and, when the opener
// was rebuilt away, still holds the focus; the focus falls to the body only as the card goes. The page below models that
// fall (a browser's focus fixup: the active element is the recorded node while it is on the page, else the body), so the
// failure the tab menu's callback repairs shows here as it does in the browser.

/** A page for the real showMenuCard and closeContextMenu: the shim's nodes (given the three members the builder reads that
 *  the factory lacks: className in step with classList, hasAttribute, isConnected, and a focus() that records its options
 *  and scrolls), a body with the strip of tabs inside its scrolling bar (#tabbar, 28 px rows in a 150 px view, the desktop
 *  cap), a document with the focus fixup and the capture listeners the builder installs per open, a window with a size and
 *  its blur listener. The strip's key handler is a stand-in for render.ts's (ArrowRight makes the next tab active), reached
 *  only by a key dispatched from a node inside the strip, so "the arrows still switch sessions" is the executed check on
 *  where the focus landed. focus() on a node scrolls the bar to the node's row when that row is out of the bar's view, as a
 *  browser's does, unless preventScroll is passed, so the scroll a plain focus() costs under a dismissing press shows here
 *  (the pressed-tab case). The document and window stand-ins carry no DOM edge (the body is a factory node whose edges the
 *  shim hid; the listener tables hold functions), so a failing dump of either is bounded without hideEdges. */
function menuPage() {
  const make = nodeFactory();
  const ROW = 28, VIEW = 150;   // one tab per row; the bar's view is the desktop cap (styles.css, --tabbar-cap)
  const focusCalls: Array<{ node: any; opts: FocusOptions | undefined }> = [];
  const mk = (tag: string): any => {
    const n = make(tag);
    Object.defineProperty(n, "className", { enumerable: false, configurable: true,
      get() { return Array.from(n.classList._s as Set<string>).join(" "); },
      set(v: string) { n.classList._s = new Set(String(v).split(/\s+/).filter(Boolean)); } });
    Object.defineProperty(n, "isConnected", { enumerable: false, configurable: true, get() { return body.contains(n); } });
    defineHidden(n, "hasAttribute", (k: string) => k in n._attrs);
    // focus records its options (the shim's own takes none), moves the focus as the shim's does, then scrolls the bar to
    // the node's row when the node is a tab whose row is out of the bar's view, as a browser's focus() does unless it is
    // given preventScroll
    const shimFocus = n.focus;
    defineHidden(n, "focus", (opts?: FocusOptions) => {
      focusCalls.push({ node: n, opts });
      shimFocus.call(n);
      if (opts && opts.preventScroll) return;
      if (typeof n._top === "number" && tabbar.contains(n) && (n._top < tabbar.scrollTop || n._top + ROW > tabbar.scrollTop + VIEW)) tabbar.scrollTop = n._top;
    });
    return n;
  };
  const body = mk("body");
  const tabbar = mk("div"); tabbar.id = "tabbar"; body.appendChild(tabbar);   // the strip's scrolling bar
  const bar = mk("div"); bar.id = "tabs"; tabbar.appendChild(bar);
  let focused: any = null, activeId = "a";
  const doc: any = {
    body, focusInWindow: true, hasFocus() { return doc.focusInWindow; },
    createElement: (tag: string) => mk(tag), getElementById: (id: string) => (id === "tabs" ? bar : null),
    get activeElement() { return focused && body.contains(focused) ? focused : body; },
    set activeElement(n: any) { focused = n; },
    _cap: {} as Record<string, Array<(ev: any) => void>>,
    addEventListener(t: string, fn: (ev: any) => void) { (doc._cap[t] ||= []).push(fn); },
    removeEventListener(t: string, fn: (ev: any) => void) { doc._cap[t] = (doc._cap[t] || []).filter((f: unknown) => f !== fn); },
    fire(t: string, ev: any) { for (const fn of (doc._cap[t] || []).slice()) fn(ev); },
  };
  const win: any = {
    innerWidth: 1200, innerHeight: 800, _l: {} as Record<string, Array<() => void>>,
    addEventListener(t: string, fn: () => void) { (win._l[t] ||= []).push(fn); },
    removeEventListener(t: string, fn: () => void) { win._l[t] = (win._l[t] || []).filter((f: unknown) => f !== fn); },
    fire(t: string) { for (const fn of (win._l[t] || []).slice()) fn(); },
  };
  // the strip: ArrowRight from a node inside it makes the next tab active (render.ts's onTabKey, as one line)
  bar.addEventListener("keydown", (ev: any) => {
    if (ev.key !== "ArrowRight") return;
    const ids: string[] = bar.children.map((c: any) => c.dataset.id);
    activeId = ids[(ids.indexOf(activeId) + 1) % ids.length];
  });
  const g: any = globalThis;
  const prev = { document: g.document, window: g.window };
  g.document = doc; g.window = win;
  return {
    doc, win, body, tabbar, bar,
    /** renderTabs on a push: every tab node is replaced, so a node held from before is detached; a tab's row is its index */
    strip(ids: string[]): any[] {
      for (const t of bar.children.slice()) t.remove();
      return ids.map((id, i) => { const t = mk("div"); t.className = "tab"; t.dataset.id = id; t.tabIndex = 0; defineHidden(t, "_top", i * ROW); bar.appendChild(t); return t; });
    },
    activeId: () => activeId,
    /** render.ts's focusActiveTab, its first rung: the active tab's node in the strip as it stands NOW, focused with the
     *  caller's options (the lift hands the callback's through) */
    focusActiveTab(opts?: FocusOptions) { const t = bar.children.find((c: any) => c.dataset.id === activeId); if (t) t.focus(opts); },
    /** the last focus() on one of the page's nodes: the node and the options it was given */
    lastFocus() { return focusCalls[focusCalls.length - 1]; },
    /** a key dispatched at `node`, bubbling up the parents as the DOM's does (the builder's document-capture listeners are
     *  fired through doc.fire, the capture phase) */
    key(node: any, key: string) { const ev = { key, preventDefault() {}, stopPropagation() {} }; for (let p = node; p; p = p.parentNode) for (const fn of ((p._stacks && p._stacks.keydown) || []).slice()) fn(ev); },
    escape() { doc.fire("keydown", { key: "Escape", preventDefault() {} }); },   // the builder's Escape: its document-capture onKey
    /** a press on `node`: the builder's document-capture pointerdown, a dismissal when the press is outside the card */
    press(node: any) { doc.fire("pointerdown", { target: node }); },
    restore() { closeContextMenu(); g.document = prev.document; g.window = prev.window; },
  };
}
type Page = ReturnType<typeof menuPage>;

/** render.ts's two close callbacks, lifted from the source by their anchors and evaluated against the page (the real
 *  contextMenuOpen, so they read the builder's own state; the page's focusActiveTab, given the options the callback
 *  passes, and document). */
function liftCloseCallbacks(page: Page): { onTabMenuClosed: () => void; onSelectionMenuClosed: () => void; setCard: (m: unknown) => void; card: () => unknown } {
  const RENDER = readWebview("render.ts");
  const a = RENDER.indexOf("\nfunction onTabMenuClosed() {");
  const b = RENDER.indexOf("\n}\n", RENDER.indexOf("\nfunction onSelectionMenuClosed() {", a)) + 3;
  assert.ok(a > 0 && b > a + 3, "onTabMenuClosed's or onSelectionMenuClosed's anchor moved in render.ts; re-anchor this lift");
  const js = requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
  const f = new Function("contextMenuOpen", "focusActiveTab", "document",
    "let ctxMenuEl = null, tagsFlyNewInput = null, tabMenuViewsHook = () => {};\n" + js +
    "\nreturn { onTabMenuClosed, onSelectionMenuClosed, setCard: (m) => { ctxMenuEl = m; }, card: () => ctxMenuEl };");
  return f(contextMenuOpen, (opts?: FocusOptions) => page.focusActiveTab(opts), page.doc);
}
const openTabMenu = (page: Page, onClose: () => void): any => {
  const menu = menuCard();
  addMenuItem(menu, { label: "Rename", pick: () => {} });
  return showMenuCard(menu, 10, 10, { onClose });
};

test("render.ts: the tab menu's close callback puts the focus on the active tab when the card holds it or it fell to the body, with the document focused; the selection menu's forgets the card and moves nothing", () => {
  const R = readWebview("render.ts");
  assert.match(R, /function onTabMenuClosed\(\) \{\s*\n\s*ctxMenuEl = null;\s*\n\s*tagsFlyNewInput = null;\s*\n\s*tabMenuViewsHook = \(\) => \{\};\s*\n\s*const card = contextMenuOpen\(\), active = document\.activeElement;\s*\n\s*if \(document\.hasFocus\(\) && \(\(card && card\.contains\(active\)\) \|\| active === document\.body\)\) focusActiveTab\(\{ preventScroll: true \}\);\s*\n\}/,
    "the three forgets first (the pins on them hold), then the refocus: the builder's own card (contextMenuOpen, still the card when the callback runs), the card holds the focus or it fell to the body, the document has the focus; taken with preventScroll, since the callback runs inside a dismissing pointerdown (the pressed-tab case below)");
  assert.match(R, /function focusActiveTab\(opts\?: FocusOptions\) \{\s*\n\s*const bar = document\.getElementById\("tabs"\);\s*\n\s*const tab = bar\?\.querySelector\(`\.tab\[data-id="\$\{activeId\}"\]`\) as HTMLElement \| null;\s*\n\s*if \(tab\) \{ tab\.focus\(opts\); return; \}\s*\n(?:\s*\/\/[^\n]*\n)*\s*const home = activeId \? homeSectionOf\(lastStripItems, activeId\) : null;\s*\n\s*if \(!home \|\| home\.name === null \|\| !bar\) return;\s*\n\s*Array\.from\(bar\.querySelectorAll<HTMLElement>\("\.tab-group-head"\)\)\.find\(\(h\) => h\.dataset\.group === home\.name\)\?\.focus\(opts\);\s*\n\}/,
    "the options ride both rungs of focusActiveTab's ladder: the tab, else its section's head");
  assert.equal(R.split("focusActiveTab({ preventScroll: true })").length - 1, 1, "one caller holds the scroll, the tab menu's close; the arrows, a pick and the send-time hop scroll the tab into view as before");
  assert.match(R, /function onSelectionMenuClosed\(\) \{\s*\n\s*ctxMenuEl = null;\s*\n\}/, "the selection menu's close is the forget alone");
  assert.match(R, /import \{[^}]*\bcontextMenuOpen\b[^}]*\} from "\.\/ctx-menu";/, "render.ts reads the open card from the builder");
  assert.equal(R.split("{ onClose: onTabMenuClosed }").length - 1, 1, "one caller of the tab menu's callback: showTabMenu");
  assert.equal(R.split("{ onClose: onSelectionMenuClosed }").length - 1, 1, "one caller of the selection menu's: showSelectionMenu");
});

test("executed: Escape on the tab menu after a push rebuilt the strip puts the focus on the active tab, taken with preventScroll, so ArrowRight still switches sessions (2026-09-17 review, correctness-1; round 2, tests-1)", () => {
  const page = menuPage();
  try {
    const [, b] = page.strip(["a", "b"]);   // a is the active session; the menu opens from a right-click on b's tab
    b.focus();
    const cb = liftCloseCallbacks(page);
    const menu = openTabMenu(page, cb.onTabMenuClosed);
    cb.setCard(menu);
    assert.ok(page.doc.activeElement === menu, "the card takes the focus at the open: " + describeNode(page.doc.activeElement));
    const [a2] = page.strip(["a", "b"]);   // the push: renderTabs swaps every tab node while the menu is open
    assert.ok(!b.isConnected, "the opener is detached");
    page.escape();
    assert.ok(contextMenuOpen() === null && cb.card() === null, "the card is closed and forgotten");
    assert.ok(page.doc.activeElement === a2, "the focus is on the active tab's fresh node, not the body: " + describeNode(page.doc.activeElement));
    assert.ok(page.lastFocus().node === a2, "the last focus() was the active tab's: " + describeNode(page.lastFocus().node));
    assert.deepEqual(page.lastFocus().opts, { preventScroll: true }, "taken with preventScroll: the same callback runs inside a dismissing pointerdown (the pressed-tab case below)");
    page.key(page.doc.activeElement, "ArrowRight");
    assert.equal(page.activeId(), "b", "an arrow from there reaches the strip's handler and switches the session");
  } finally { page.restore(); }
});

test("executed: a press on another tab that dismisses the menu after a push rebuilt the strip leaves the bar's scrollTop where it was, so the pressed tab stays under the pointer and its click lands (review round 2, tests-1 and ui-1)", () => {
  // the failure: the callback runs inside the dismissing pointerdown, and a plain focus() on the active tab (its row out of
  // view) scrolled the bar before the release; the mouseup hit the tab that had scrolled in, the click fired on #tabs where
  // the delegate names no tab, and the press selected nothing (both engines, real geometry, per the round's refuters)
  const page = menuPage();
  try {
    // twelve tabs, one per row: the active tab a is in the top row, the bar is scrolled so rows 8 to 12 are in view and
    // a's row is not; the menu opens from a right-click on the last tab, then a push rebuilds the strip under it
    const ids = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"];
    const first = page.strip(ids);
    page.tabbar.scrollTop = 200;
    first[11].focus();
    assert.equal(page.tabbar.scrollTop, 200, "the right-clicked tab is in view: its focus scrolls nothing");
    const cb = liftCloseCallbacks(page);
    cb.setCard(openTabMenu(page, cb.onTabMenuClosed));
    const fresh = page.strip(ids);
    assert.ok(!first[11].isConnected && contextMenuOpen() !== null, "the opener is detached and the menu is still open");
    // the press on a visible tab: the builder's pointerdown capture closes the card, whose callback refocuses the active tab
    page.press(fresh[9]);
    assert.ok(contextMenuOpen() === null && cb.card() === null, "the press closed the card");
    assert.equal(page.tabbar.scrollTop, 200, "the bar did not move under the pointer: the refocus held the scroll");
    assert.ok(page.doc.activeElement === fresh[0], "the focus is on the active tab's fresh node: " + describeNode(page.doc.activeElement));
    assert.deepEqual(page.lastFocus().opts, { preventScroll: true }, "taken with preventScroll");
    // the control: the arrows' plain focusActiveTab() does scroll the active tab's row into view, so the fake sees the scroll
    // the press case holds (and the trade the fix accepts: after an Escape the ring may sit off screen until the first arrow)
    page.focusActiveTab();
    assert.equal(page.tabbar.scrollTop, 0, "a plain focus() scrolls the bar to the active tab's row");
  } finally { page.restore(); }
});

test("executed: the plain close (the selection menu's) moves no focus: with the opener rebuilt away the focus falls to the body with the card and an arrow switches nothing (the failure the tab menu's callback repairs, reproduced)", () => {
  const page = menuPage();
  try {
    const [, b] = page.strip(["a", "b"]);
    b.focus();
    const cb = liftCloseCallbacks(page);
    cb.setCard(openTabMenu(page, cb.onSelectionMenuClosed));
    page.strip(["a", "b"]);
    page.escape();
    assert.ok(cb.card() === null, "the card is forgotten");
    assert.ok(page.doc.activeElement === page.body, "the focus fell to the body: " + describeNode(page.doc.activeElement));
    page.key(page.doc.activeElement, "ArrowRight");
    assert.equal(page.activeId(), "a", "the arrow from the body reaches no strip handler");
  } finally { page.restore(); }
});

test("executed: the tab menu's callback moves the focus MINIMALLY: a standing opener gets it back from the builder (the right-clicked tab, not the active one); a close under the window's blur moves nothing", () => {
  const page = menuPage();
  try {
    const [a, b] = page.strip(["a", "b"]);
    b.focus();
    const cb = liftCloseCallbacks(page);
    cb.setCard(openTabMenu(page, cb.onTabMenuClosed));
    page.escape();
    assert.ok(page.doc.activeElement === b, "no push: the builder hands the focus back to the right-clicked tab and the callback leaves it there: " + describeNode(page.doc.activeElement));
    assert.ok(page.doc.activeElement !== a, "the active tab is not pulled in over a standing opener");
    // the window's blur while the strip was rebuilt: the document has lost the focus, so nothing is refocused
    cb.setCard(openTabMenu(page, cb.onTabMenuClosed));
    page.strip(["a", "b"]);
    page.doc.focusInWindow = false;
    page.win.fire("blur");
    assert.ok(contextMenuOpen() === null, "the blur closed the card");
    assert.ok(page.doc.activeElement === page.body, "and moved no focus in a document that has none: " + describeNode(page.doc.activeElement));
  } finally { page.restore(); }
});
