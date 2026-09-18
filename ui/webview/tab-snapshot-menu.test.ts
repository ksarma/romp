// THE ROW'S CONTEXT MENU IN THE SECTION VIEW (the user 2026-09-18, who wanted a hidden session, which has no tab on the strip,
// to reach its per-session settings from the place its tab would be: the tag's at-a-glance view). A right-click on a row (the
// engines dispatch a long-press and the keyboard's menu key the same way) opens THE TAB'S MENU for the row's session, built by
// showTabMenu itself with the section the view shows as the copy, so the rows are the tab menu's own. EXECUTED: render.ts's
// pane block (snapView through fillSnapshotRow, with the host's contextmenu listener and rowHasTabMenu), its showTabMenu, its
// startTabRename and the shared builder (ctx-menu.ts) are transpiled when the test runs and evaluated in ONE scope over a
// fake DOM (the pane test's selector engine and focus fixup, the menu door test's rect model and row helpers) with the real
// pure modules (tab-groups, tab-snapshot, tab-snapshot-view, status-chip, actions, host-prefix); a slice that stops compiling
// against the stand-in fails loudly here (a ReferenceError). Read off the code the page runs:
//   - a right-click on a HIDDEN session's row opens a menu whose rows equal, row for row, the ones showTabMenu builds when the
//     strip's tab handler calls it for the same session and the same copy (the tab's dataset.copy for that section); the same
//     for a shown row; the rows DIFFER from a call with no copy (the Hide tab row leaves under two holders), so the copy the
//     view passes is what makes the rows the tab's; the failure message names the first row that differs by its label;
//   - the Hide tab row on the hidden row's menu reads Show tab and its click writes the show for THAT section;
//   - where the strip has no menu the row has none: a subagent viewer's session, a placeholder (the kernel still building the
//     session); a skeleton's row opens it; the heading, the fold's head and the host's gaps leave the engine's own menu;
//   - the keyboard's contextmenu (clientX and clientY at 0) seats the menu at the row's bottom-left corner (menuAnchor);
//   - Rename from the row's menu edits the name ON THE ROW: the input stands where the row's button was, a push while editing
//     is held (the strip's rename hold covers the view) and flushed at the end, Enter posts renameSession with the new name
//     and hands the focus back to the row, Escape posts nothing; with the view closed the tab's label is edited, as before;
//   - source pins on the strip's two wirings, the host's listener, the hold, the sheet and the docs.
// The notes-api demo world, synthetic ids, no real data.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { hideEdges, staysEnumerable } from "../test-dom-shim";
import { viewTagUnion } from "./session-views";
import { parseTabGroups, readTabGroups, writeTabGroups, prunePinned, sectionRef, isPinned, setPinned, isHidden, setHidden, planStrip, setSectionCollapsed,
         homeSectionOf, neighborOfFolded, headWords, TABGROUPS_KEY, TABGROUPS_EVENT, type StripHead, type SectionRef } from "./tab-groups";
import { snapshotModel, snapshotHeading, rowWords, hiddenNeeds, hiddenFoldWords, actWords, standInPip } from "./tab-snapshot";
import { rowStillOpen, installSnapshotEscape, reconcileRows, repeatedClick, menuAnchor } from "./tab-snapshot-view";
import { sectionPip, sectionPipMembers, sectionPipTitle, sectionTodoFlag, sectionTodoPhrase, sectionDoorTitle } from "./tab-state";
import { statusChip } from "./status-chip";
import { hostPrefix } from "./host-prefix";
import { pressHold } from "./actions";
import { renderKind } from "./skeleton-tabs";
import { RENAME_SUBLINE } from "./clear-confirm";
import { KEYS_EVENT } from "./keybindings";

const requireCjs = createRequire(__filename);
const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");
const RENDER = ui("webview", "render.ts");
const CTX = ui("webview", "ctx-menu.ts");
const CSS = ui("webview", "styles.css");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");
const REF = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "reference.md"), "utf8");

/** a verbatim slice of render.ts between two markers, both of which must exist */
function slice(src: string, from: string, to: string, after = 0): string {
  const a = src.indexOf(from, after), b = src.indexOf(to, a + 1);
  assert.ok(a >= 0 && b > a, `markers moved: ${from.slice(0, 60)} .. ${to.slice(0, 60)}; re-anchor`);
  return src.slice(a, b);
}
const SNAP = slice(RENDER, "let snapView: string | null = null;", "function showActive(");
const MENU_AT = RENDER.indexOf("function showTabMenu(e: MouseEvent, id: string, copy?: string) {");
const MENU_TAIL = RENDER.indexOf("seatMenu(e.clientX, e.clientY);", MENU_AT);
const MENU_END = RENDER.indexOf("\n}\n", MENU_TAIL) + 3;
assert.ok(MENU_AT > 0 && MENU_TAIL > MENU_AT && MENU_END > MENU_TAIL, "showTabMenu's anchors moved; re-anchor this lift");
const MENU = RENDER.slice(MENU_AT, MENU_END);
const RENAME = slice(RENDER, "function startTabRename(id: string, copy?: string) {", "// Keyboard nav on a focused tab");
const FLY_AT = RENDER.indexOf("const HOVER_INTENT_MS = 120;");
const FLY = RENDER.slice(FLY_AT, RENDER.indexOf("\n}\n", RENDER.indexOf("function wireFlyout(", FLY_AT)) + 3);
const NOTIFIER = RENDER.match(/\nfunction viewsChanged\(\) \{ tabMenuViewsHook\(\); \}\n/);
const MEDIA = RENDER.match(/const PHONE_LAYOUT_MEDIA = "([^"]+)";/);
assert.ok(FLY_AT > 0 && NOTIFIER && MEDIA, "wireFlyout's, the notifier's or the media rule's anchor moved; re-anchor this lift");
const CTX_AT = CTX.indexOf("const MARGIN = 4;");
const BUILDER = CTX.slice(CTX_AT, CTX.indexOf("\n}\n", CTX.indexOf("export function showMenuCard(", CTX_AT)) + 3).replace(/^export /gm, "");
assert.ok(CTX_AT > 0 && BUILDER.includes("function showMenuCard("), "the builder's anchors moved (ctx-menu.ts); re-anchor this lift");

// ── the fake DOM: the pane test's selector engine and focus fixup, the menu door test's rect model and row readers ──
type Compound = { scope: boolean; id: string | null; classes: string[]; attrs: Array<[string, string | null]> };
function parseCompound(s: string): Compound {
  const c: Compound = { scope: false, id: null, classes: [], attrs: [] };
  for (const m of s.matchAll(/:scope|#([\w-]+)|\.([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]/g)) {
    if (m[0] === ":scope") c.scope = true; else if (m[1]) c.id = m[1]; else if (m[2]) c.classes.push(m[2]); else if (m[3]) c.attrs.push([m[3], m[4] ?? null]);
  }
  return c;
}
function parseSelector(sel: string): Array<{ c: Compound; comb: ">" | " " | null }> {
  const parts = sel.trim().split(/\s*>\s*|\s+/);
  const combs = sel.trim().match(/\s*>\s*|\s+/g) || [];
  return parts.map((p, i) => ({ c: parseCompound(p), comb: i === 0 ? null : (combs[i - 1].includes(">") ? ">" : " ") as ">" | " " | null }));
}
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
let FOCUS: FakeEl | null = null;   // the page's focus, as the document's activeElement reads it
const camel = (k: string) => k.replace(/-([a-z])/g, (_, c: string) => c.toUpperCase());
class FakeEl {
  tag: string; className: string; id = "";
  children!: FakeEl[]; parent!: FakeEl | null;   // the edges, non-enumerable (ui/test-dom-shim.ts hideEdges): a node inspects as its primitives
  text = ""; title = ""; tabIndex = -1; type = ""; disabled = false; draggable = false; value = ""; placeholder = ""; spellcheck = true; size = 0;
  innerHTML = ""; isContentEditable = false; scrollTop = 0; scrollHeight = 0; clientHeight = 0;
  selectionStart = 0; selectionEnd = 0; selectionDirection = "none";
  rect: Rect | null = null;   // a test's own rect for a node the rect model below does not place (a row)
  style: Record<string, any> = { display: "", background: "", color: "", left: "", top: "", setProperty(k: string, v: string) { (this as Record<string, string>)[k] = v; } };
  dataset: Record<string, string> = {}; attrs: Record<string, string> = {}; listeners: Record<string, Function[]> = {};
  constructor(tag: string, cls = "") {
    this.tag = tag; this.className = cls;
    Object.defineProperty(this, "children", { value: [], writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "parent", { value: null, writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  static text(s: string): FakeEl { const t = new FakeEl("#text"); t.text = s; return t; }
  get textContent(): string { return this.text + this.children.map((c) => c.textContent).join(""); }
  set textContent(v: string) { this.text = v; this.children.length = 0; }
  has(x: string): boolean { return this.className.split(/\s+/).includes(x); }
  get classList() {
    const self = this;
    return { add(...c: string[]) { for (const x of c) if (!self.has(x)) self.className = (self.className + " " + x).trim(); },
             remove(...c: string[]) { for (const x of c) self.className = self.className.split(/\s+/).filter((y) => y && y !== x).join(" "); },
             contains(x: string) { return self.has(x); },
             toggle(x: string, on?: boolean) { if (on === undefined ? !self.has(x) : on) this.add(x); else this.remove(x); } };
  }
  get childElementCount(): number { return this.children.filter((c) => c.tag !== "#text").length; }
  get firstChild(): FakeEl | null { return this.children[0] ?? null; }
  get firstElementChild(): FakeEl | null { return this.children.find((c) => c.tag !== "#text") ?? null; }
  get lastElementChild(): FakeEl | null { const els = this.children.filter((c) => c.tag !== "#text"); return els[els.length - 1] ?? null; }
  get parentNode(): FakeEl | null { return this.parent; }
  get parentElement(): FakeEl | null { return this.parent; }
  get isConnected(): boolean { let n: FakeEl | null = this; while (n) { if (n.tag === "body") return true; n = n.parent; } return false; }
  get offsetWidth(): number { return this.getBoundingClientRect().width; }
  appendChild(c: FakeEl): FakeEl { return this.insertBefore(c, null); }
  append(...cs: Array<FakeEl | string>): void { for (const c of cs) this.appendChild(typeof c === "string" ? FakeEl.text(c) : c); }
  replaceChildren(...cs: FakeEl[]): void { for (const c of [...this.children]) this.removeChild(c); this.append(...cs); }
  insertBefore(c: FakeEl, ref: FakeEl | null): FakeEl {
    if (c.parent) { const p = c.parent; p.children = p.children.filter((x) => x !== c); c.parent = null; if (FOCUS && c.contains(FOCUS)) FOCUS = BODY; }
    c.parent = this;
    const j = ref ? this.children.indexOf(ref) : -1;
    if (j < 0) this.children.push(c); else this.children.splice(j, 0, c);
    return c;
  }
  removeChild(c: FakeEl): FakeEl { this.children = this.children.filter((x) => x !== c); c.parent = null; if (FOCUS && c.contains(FOCUS)) FOCUS = BODY; return c; }
  remove(): void { this.parent?.removeChild(this); }
  after(...cs: FakeEl[]): void { const p = this.parent!; let ref: FakeEl | null = p.children[p.children.indexOf(this) + 1] ?? null; for (const c of cs) p.insertBefore(c, ref); }
  before(...cs: FakeEl[]): void { const p = this.parent!; for (const c of cs) p.insertBefore(c, this); }
  /** the DOM's contract: null and undefined answer false; any other non-node throws (the builder's scroll guard is held by its instanceof) */
  contains(n: unknown): boolean {
    if (n === null || n === undefined) return false;
    if (!(n instanceof FakeEl)) throw new TypeError("Failed to execute 'contains' on 'Node': parameter 1 is not of type 'Node'.");
    let c: FakeEl | null = n; while (c) { if (c === this) return true; c = c.parent; } return false;
  }
  setAttribute(k: string, v: string): void { if (k.startsWith("data-")) this.dataset[camel(k.slice(5))] = v; else this.attrs[k] = v; }
  getAttribute(k: string): string | null { if (k.startsWith("data-")) return this.dataset[camel(k.slice(5))] ?? null; return this.attrs[k] ?? null; }
  hasAttribute(k: string): boolean { return this.getAttribute(k) !== null; }
  addEventListener(t: string, f: Function): void { (this.listeners[t] ??= []).push(f); }
  removeEventListener(t: string, f: Function): void { this.listeners[t] = (this.listeners[t] ?? []).filter((g) => g !== f); }
  fire(t: string, ev: any = {}): void { for (const f of [...(this.listeners[t] ?? [])]) f(ev); }
  /** as an engine: a node inside a display:none subtree is not focusable, so focus() moves nothing (the editor's focus-took check reads this) */
  focus(): void { for (let n: FakeEl | null = this; n; n = n.parent) if (n.style.display === "none") return; FOCUS = this; }
  blur(): void { if (FOCUS === this) FOCUS = BODY; }
  select(): void {}
  setSelectionRange(a: number, b: number, dir = "none") { this.selectionStart = a; this.selectionEnd = b; this.selectionDirection = dir; }
  click(): void { this.fire("click", { stopPropagation() {}, preventDefault() {}, detail: 1, target: this }); }
  matches1(c: Compound, scope: FakeEl): boolean {
    if (c.scope && this !== scope) return false;
    if (c.id !== null && this.id !== c.id) return false;
    if (!c.classes.every((x) => this.has(x))) return false;
    return c.attrs.every(([k, v]) => (v === null ? this.getAttribute(k) !== null : this.getAttribute(k) === v));
  }
  matchesChain(chain: ReturnType<typeof parseSelector>, i: number, scope: FakeEl): boolean {
    if (!this.matches1(chain[i].c, scope)) return false;
    if (i === 0) return true;
    if (chain[i].comb === ">") return !!this.parent && this.parent.matchesChain(chain, i - 1, scope);
    for (let p = this.parent; p; p = p.parent) if (p.matchesChain(chain, i - 1, scope)) return true;
    return false;
  }
  *walk(): Generator<FakeEl> { for (const c of this.children) { yield c; yield* c.walk(); } }
  querySelectorAll(sel: string): FakeEl[] { const chain = parseSelector(sel); return [...this.walk()].filter((n) => n.tag !== "#text" && n.matchesChain(chain, chain.length - 1, this)); }
  querySelector(sel: string): FakeEl | null { return this.querySelectorAll(sel)[0] ?? null; }
  closest(sel: string): FakeEl | null { const chain = parseSelector(sel); for (let n: FakeEl | null = this; n; n = n.parent) if (n.matchesChain(chain, chain.length - 1, n)) return n; return null; }
  byId(id: string): FakeEl | null { if (this.id === id) return this; for (const c of this.children) { const f = c.byId(id); if (f) return f; } return null; }
  /** THE RECT MODEL (the menu door test's): a menu card stands where its style put it and is as tall as its rows, one ROW each;
   *  a row's rect is its slot under the card's top; a node a test placed (`rect`) has that; anything else a fixed small box */
  static ROW = 30;
  rows(): FakeEl[] { return this.children.filter((c) => c.tag !== "#text" && !c.has("ctx-sub")); }
  getBoundingClientRect(): Rect {
    const num = (v: string | undefined) => parseFloat(v || "0") || 0;
    if (this.rect) return this.rect;
    if (this.has("ctx-menu")) {
      const width = this.has("ctx-sub") ? 200 : 300, height = this.rows().length * FakeEl.ROW, left = num(this.style.left), top = num(this.style.top);
      return { left, top, right: left + width, bottom: top + height, width, height };
    }
    if (this.parent && this.parent.has("ctx-menu")) {
      const pr = this.parent.getBoundingClientRect(), i = this.parent.rows().indexOf(this);
      return { left: pr.left, top: pr.top + i * FakeEl.ROW, right: pr.right, bottom: pr.top + (i + 1) * FakeEl.ROW, width: pr.width, height: FakeEl.ROW };
    }
    return { left: 0, top: 0, right: 120, bottom: 20, width: 120, height: 20 };
  }
  /** every descendant, depth first, self included */
  all(): FakeEl[] { return [this, ...this.children.flatMap((c) => c.all())]; }
  label(): string | undefined { return this.all().find((n) => n.has("ctx-item-label"))?.textContent; }
  sub(): string | undefined { return this.all().find((n) => n.has("ctx-item-sub"))?.textContent; }
  icon(): FakeEl | undefined { return this.all().find((n) => n.has("ctx-icon")); }
}
class HTMLButtonElement extends FakeEl {}
let BODY = new FakeEl("body");

/** the page's window: the pane's size, the listeners the slices install (capture and bubble kept apart for installSnapshotEscape),
 *  and the release target pressHold installs its listeners on */
class FakeWin {
  innerWidth = 1200; innerHeight = 800;
  listeners: Record<string, Array<{ fn: Function; cap: boolean }>> = {};
  addEventListener(k: string, fn: Function, cap?: boolean | object) { (this.listeners[k] ??= []).push({ fn, cap: cap === true || (typeof cap === "object" && !!(cap as any).capture) }); }
  removeEventListener(k: string, fn: Function) { this.listeners[k] = (this.listeners[k] ?? []).filter((l) => l.fn !== fn); }
  fire(k: string, ev: any = {}) { for (const l of [...(this.listeners[k] ?? [])].sort((a, b) => Number(b.cap) - Number(a.cap))) l.fn(ev); }
  setTimeout() { return 0; }
  clearTimeout() {}
  matchMedia(_q: string) { return { matches: false, addEventListener: (k: string, fn: Function) => this.addEventListener("media:" + k, fn) }; }
  dispatchEvent() { return true; }
}

type Hooks = {
  content: FakeEl; bar: FakeEl; win: FakeWin;
  sessions: Map<string, any>; ledgers: Map<string, any>; tabMeta: Map<string, any>; closingTabs: Map<string, number>; skeleton: Set<string>;
  lastStripItems: any[]; order: string[]; collapsed: Set<string>; nowMs: number; tagViews: any; known: string[];
  calls: string[]; delegates: Array<{ root: FakeEl; handlers: Record<string, Function> }>; writes: any[]; flags: any[]; posts: any[]; renders: number; dismissed: number;
};
type Api = {
  renderSnapshot: () => boolean; hideSnapshot: () => void; snapshotHost: () => FakeEl | null;
  showTabMenu: (e: { clientX: number; clientY: number }, id: string, copy?: string) => FakeEl | null;
  startTabRename: (id: string, copy?: string) => void; dismiss: () => void;
  get: () => { snapView: string | null; ctxMenuEl: FakeEl | null; ctxMenuAt: { x: number; y: number } | null; renameActive: boolean; renderPendingAfterRename: boolean; tabPointerHeld: boolean; tabMenuSeat: string; rowRenameEnd: boolean; renders: number };
  set: (p: Record<string, unknown>) => void;
};

function lift(): (H: Hooks) => Api {
  const js = requireCjs("esbuild").transformSync(SNAP + MENU + RENAME + NOTIFIER![0] + BUILDER + FLY, { loader: "ts" }).code;
  const prelude = `
    const H = HOOKS;
    const { FakeEl, HTMLButtonElement, viewTagUnion, readTabGroups, writeTabGroups, prunePinned, sectionRef, isPinned, setPinned, isHidden, setHidden, pressHold: pressHoldReal,
            TABGROUPS_KEY, TABGROUPS_EVENT, KEYS_EVENT, RENAME_SUBLINE, hostPrefix, renderKind, statusChip: statusChipReal,
            snapshotModel, snapshotHeading, rowWords, hiddenNeeds, hiddenFoldWords, actWords, standInPip, rowStillOpen, installSnapshotEscape, reconcileRows, repeatedClick, menuAnchor,
            homeSectionOf, neighborOfFolded, setSectionCollapsed, headWords, sectionPip, sectionPipMembers, sectionPipTitle, sectionTodoFlag, sectionTodoPhrase, sectionDoorTitle } = H.mods;
    const HTMLElement = FakeEl, Node = FakeEl;
    const PHONE_LAYOUT_MEDIA = ${JSON.stringify(MEDIA![1])};
    const window = H.win;
    const pressHold = (surface) => pressHoldReal(surface, window);
    // the page's document: the body the card mounts on, the ids the slices fetch, the selector queries startTabRename makes, the
    // focus, and the capture listeners the builder installs per open (recorded and fired like the window's)
    const document = {
      get body() { return H.body; },
      get activeElement() { return H.focus(); },
      hasFocus: () => true,
      getElementById: (id) => H.body.byId(id),
      querySelector: (sel) => H.body.querySelector(sel),
      createElement: (tag) => (tag === "button" ? new HTMLButtonElement(tag) : new FakeEl(tag)),
      createTextNode: (t) => FakeEl.text(t),
      listeners: {}, addEventListener(k, fn) { (this.listeners[k] ||= []).push(fn); }, removeEventListener(k, fn) { this.listeners[k] = (this.listeners[k] || []).filter((f) => f !== fn); },
      fire(k, ev = {}) { for (const fn of (this.listeners[k] || []).slice()) fn(ev); },
    };
    const Date = { now: () => H.nowMs };
    const el = (tag, cls) => { const e = document.createElement(tag); if (cls) e.className = cls; return e; };
    // the page's state the slices read and write, as render.ts declares it
    let activeId = "web", tabPointerHeld = false, renderPendingWhilePressed = false, draggedGroup = null;
    let renameActive = false, renderPendingAfterRename = false, fedMissing = false;
    let ctxMenuEl = null, ctxMenuAt = null, metaMenuEl = null, citePreviewEl = null, openCommentKey = null;
    let tabMenuViewsHook = () => {}, tagsFlyNewInput = null, pendingSessionViews = null;
    let tabMenuSeat = "tab", rowRenameEnd = null;   // the menu's seat (set at the open; the view's listener says "row") and the open row editor's end
    const settings = { stripGroupRows: false, tabsLocked: false };
    let order = H.order, lastStripItems = H.lastStripItems, collapsedTabIds = H.collapsed;
    const sessions = H.sessions, ledgers = H.ledgers, tabMeta = H.tabMeta, closingTabs = H.closingTabs, views = new Map();
    const skeletonTabs = { ids: H.skeleton };
    const paletteColors = ["#4EC9B0", "#DD42FF"];
    const vscodeApi = { postMessage: (m) => { H.posts.push(m); } };
    const location = { protocol: "https:" };
    // the strip and the page around the pane, as stubs that record
    const delegate = (root, handlers) => { H.delegates.push({ root, handlers }); };
    const setActive = (id) => { H.calls.push("setActive:" + id); activeId = id; };
    // render.ts's renderTabs, as far as the pane sees it: the rename hold defers it, else it renders the view (stripAftermath)
    const renderTabs = () => { H.renders++; if (renameActive) { renderPendingAfterRename = true; return; } if (snapView) renderSnapshot(); };
    const showActive = () => { H.calls.push("showActive"); };
    const focusActiveTab = () => { H.calls.push("focusActiveTab"); };
    const focusComposerOrAsk = () => false;
    const isTypingTarget = (t) => !!t && t.typing === true;
    const agehms = (s) => Math.floor(s) + "s";
    const ageColorReadable = (s) => "age-" + Math.floor(s);
    const hostNameNodes = (name) => [document.createTextNode(name)];
    const statusChip = (w, tag) => statusChipReal(w, tag, document);
    const tagChip = (label) => { const c = el("span", "tag-chip"); c.textContent = label; return c; };
    const tabEmojiNode = () => null;
    const ringSwitch = () => () => true;
    const dragImageBlank = () => el("div"); const hideTabTip = () => {};
    const whenChatVisible = (f) => f(); const writeScroll = () => {};
    class NavHistory { constructor() {} }
    const cssEscape = (s) => s.replace(/"/g, '\\\\"');
    // the menu's page: the flags and the dialogs it opens are recorders or inert; the store and the unions are real
    const inRompShell = () => false;
    const keyHint = () => "";
    const ctxIcon = (kind, off) => { const sp = el("span", "ctx-icon" + (off ? " off" : "")); sp.dataset.kind = kind; return sp; };
    const dismissTabMenu = () => { closeContextMenu(); };
    const onTabMenuClosed = () => { H.dismissed++; ctxMenuEl = null; tagsFlyNewInput = null; tabMenuViewsHook = () => {}; };
    const closeEmojiPrompt = () => {};
    let emojiPrompt = null;
    const setSessionFlag = (id, k, v) => { H.flags.push([id, k, v]); };
    const setSessionColor = () => {}, showMovePrompt = () => {}, showEmojiPrompt = () => {};
    const billingSubText = () => "";
    const postTagEdit = (nv) => { H.tagViews = nv; }, syncNewTagInput = () => {}, createInFlight = () => false, viewsWrites = [];
    const viewTags = (v) => (v && v.tags) || [];
    const effViews = () => H.tagViews;
    const phoneLayout = () => false;
    const knownTabIds = () => new Set(H.known);
    const reachableHosts = () => new Set();
    function tabGroups() { return readTabGroups(viewTagUnion(effViews())); }
    function writeTabGroupsPruned(st) { const out = prunePinned(st, viewTagUnion(effViews()), knownTabIds(), reachableHosts()); H.writes.push(out); writeTabGroups(out); }
    const browseRouteNow = () => "pane", openBrowse = () => {};
  `;
  const epilogue = `
    return { renderSnapshot, hideSnapshot, snapshotHost,
      showTabMenu: (e, id, copy) => { showTabMenu(e, id, copy); return ctxMenuEl; },
      startTabRename, dismiss: dismissTabMenu,
      get: () => ({ snapView, ctxMenuEl, ctxMenuAt, renameActive, renderPendingAfterRename, tabPointerHeld, tabMenuSeat, rowRenameEnd: !!rowRenameEnd, renders: H.renders }),
      set: (p) => { for (const k of Object.keys(p)) {
        if (k === "snapView") snapView = p[k]; else if (k === "activeId") activeId = p[k]; else if (k === "lastStripItems") lastStripItems = p[k];
        else if (k === "collapsedTabIds") collapsedTabIds = p[k]; else if (k === "order") order = p[k];
        else if (k === "tabMenuSeat") tabMenuSeat = p[k]; else if (k === "tabsLocked") settings.tabsLocked = p[k];
        else throw new Error("unknown knob " + k); } } };
  `;
  return new Function("HOOKS", prelude + js + epilogue) as (H: Hooks) => Api;
}
const LIFTED = lift();

/** the store the menu and the view read and write: a Map behind localStorage for the test's body (the menu door test's idiom) */
function withStore<T>(fn: (store: Map<string, string>) => T): T {
  const store = new Map<string, string>();
  const g: any = globalThis;
  const saved = g.localStorage;
  g.localStorage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => { store.set(k, v); }, removeItem: (k: string) => { store.delete(k); } };
  try { return fn(store); } finally { g.localStorage = saved; }
}

const T0 = 1781100000;
// a FOURTH member, remote (round 1 of the review, 2026-09-18): a federated session's id and name both carry the "host:" prefix
// federation prepends (host-prefix.ts hostPrefix reads the sid's prefix and strips it from the name), so its row's Rename seats
// the strip's fixed prefix span before the input and posts the bare name; a synthetic host and uuid, never real data
const REMOTE = "TESTHOST:11111111-2222-3333-4444-000000000099";
const REMOTE_NAME = "TESTHOST:remote";
// the notes-api world: infra holds web, api, tests and the remote; qa holds api and tests, so api and tests are under TWO tags (T264b:
// a copy in each section), which is what makes the copy the view passes matter: with no copy named the menu has no Hide tab row for them
const VIEWS = { active: "all", tags: [
  { id: "g1", name: "infra", color: "#4EC9B0", members: ["web", "api", "tests", REMOTE] },
  { id: "g2", name: "qa", color: "#DD42FF", members: ["api", "tests"] },
], seq: 3 };
const V = VIEWS;
const INFRA: SectionRef = { name: "infra", localId: "g1" };
/** the same world with api under infra ALONE: hidden there, it has no tab anywhere (the one-surface case) */
const V1 = { ...VIEWS, tags: [VIEWS.tags[0], { ...VIEWS.tags[1], members: ["tests"] }] };
const IDS = ["web", "api", "tests", REMOTE];
type World = { H: Hooks; api: Api; host: FakeEl; bar: FakeEl };
/** the page: #content and #tabs under the body, the strip's plan from the store (api hidden in infra unless told otherwise), the view of infra up */
function world(opts: { hide?: boolean; sub?: string[]; skeleton?: string[]; placeholder?: string[]; view?: string | null; single?: boolean } = {}): World {
  BODY = new FakeEl("body"); FOCUS = BODY;
  const V = opts.single ? V1 : VIEWS;
  const content = new FakeEl("div"); content.id = "content"; BODY.appendChild(content);
  const bar = new FakeEl("div"); bar.id = "tabs"; BODY.appendChild(bar);
  const unions = viewTagUnion(V);
  let groups = parseTabGroups(null, unions);
  if (opts.hide !== false) groups = setHidden(groups, INFRA, "api", true);
  writeTabGroups(groups);   // the store the menu's tabGroups() and the view's setRowHidden read
  const plan = planStrip(IDS, unions, readTabGroups(unions), "web", false);
  // the strip's tabs for the plan (a stand-in for renderTabs' loop: id and copy, a label), so startTabRename can find one when the view is not up
  let copyGroup: string | null | undefined;   // renderTabs' rule: a tab's copy is the header before it
  for (const it of plan.items) {
    if ("head" in it) { const h = new FakeEl("div", "tab-group-head"); h.dataset.group = String(it.head.name); bar.appendChild(h); copyGroup = it.head.name; continue; }
    const t = new FakeEl("div", "tab"); t.dataset.id = it.id; if (copyGroup !== undefined) t.dataset.copy = copyGroup ?? "";
    const l = new FakeEl("span", "tab-label"); l.textContent = it.id; t.appendChild(l); bar.appendChild(t);
  }
  const sessions = new Map<string, any>([
    ["web", { name: "web", color: { bg: "#3a7bd5", fg: "#ffffff" }, status: { state: "working", sinceEpoch: (T0 - 30) * 1000 }, events: [], cwd: "/srv/notes-api/web" }],
    ["api", { name: "api", color: { bg: "#d53a3a", fg: "#ffffff" }, status: { state: "idle", sinceEpoch: (T0 - 600) * 1000 }, events: [], userTodos: [] }],
    ["tests", { name: "tests", color: null, status: { state: "ready" }, events: [] }],
    [REMOTE, { name: REMOTE_NAME, color: { bg: "#3a86ff", fg: "#ffffff" }, status: { state: "ready" }, events: [] }],
  ]);
  for (const id of opts.sub ?? []) sessions.get(id).sub = { parent: "web", agent: "a1" };   // a subagent viewer: read-only, no menu on its tab
  for (const id of opts.placeholder ?? []) sessions.delete(id);   // the kernel still building it: no frame, no skeleton
  const ledgers = new Map<string, any>([
    ["web", { summary: "Building the notes-api web pages", needsInput: false, tree: [{ text: "Add the notes list page", current: true }] }],
    ["api", { summary: "Designing the notes schema", needsInput: true, tree: [] }],
    ["tests", { summary: "Running the suite", needsInput: false, tree: [] }],
    [REMOTE, { summary: "Indexing the notes on the other machine", needsInput: false, tree: [] }],
  ]);
  const H: Hooks & { mods: Record<string, unknown>; body: FakeEl; focus: () => FakeEl | null } = {
    content, bar, win: new FakeWin(), sessions, ledgers, tabMeta: new Map(IDS.map((id) => [id, { name: id, color: null }])), closingTabs: new Map(),
    skeleton: new Set(opts.skeleton ?? []), lastStripItems: plan.items, order: IDS, collapsed: plan.folded, nowMs: T0 * 1000, tagViews: V, known: IDS,
    calls: [], delegates: [], writes: [], flags: [], posts: [], renders: 0, dismissed: 0,
    body: BODY, focus: () => FOCUS,
    mods: { FakeEl, HTMLButtonElement, viewTagUnion, readTabGroups, writeTabGroups, prunePinned, sectionRef, isPinned, setPinned, isHidden, setHidden, pressHold,
            TABGROUPS_KEY, TABGROUPS_EVENT, KEYS_EVENT, RENAME_SUBLINE, hostPrefix, renderKind, statusChip,
            snapshotModel, snapshotHeading, rowWords, hiddenNeeds, hiddenFoldWords, actWords, standInPip, rowStillOpen, installSnapshotEscape, reconcileRows, repeatedClick, menuAnchor,
            homeSectionOf, neighborOfFolded, setSectionCollapsed, headWords, sectionPip, sectionPipMembers, sectionPipTitle, sectionTodoFlag, sectionTodoPhrase, sectionDoorTitle },
  };
  const api = LIFTED(H);
  api.set({ snapView: opts.view === undefined ? "infra" : opts.view });
  if (opts.view !== null) assert.equal(api.renderSnapshot(), true, "the view of infra paints");
  const host = content.byId("tab-snapshot")!;
  return { H, api, host, bar };
}
const itemOf = (host: FakeEl, id: string) => host.querySelector(`.snap-item[data-id="${id}"]`)!;
/** open the Hidden fold the way the user does: a click on its head through the host's delegate (the rows under it become rendered) */
function openFold(H: Hooks, host: FakeEl) {
  const head = host.querySelector(".snap-hidden-head")!;
  H.delegates[0].handlers["toggle-hidden"](head, { detail: 1 });
  assert.equal(host.querySelector(".snap-hidden-list")!.style.display, "", "the fold is open");
}
const rowOf = (host: FakeEl, id: string) => itemOf(host, id).querySelector(":scope > .snap-row")!;
/** a right-click as the engine dispatches it: at the row's button, bubbling to the host's listener */
function rightClick(host: FakeEl, target: FakeEl, x = 40, y = 300) {
  const ev = { target, clientX: x, clientY: y, prevented: false, stopped: false, preventDefault() { this.prevented = true; }, stopPropagation() { this.stopped = true; } };
  host.fire("contextmenu", ev);
  return ev;
}
/** what a menu shows, row by row: the classes, the words, the tooltip, the icon, the swatches; enough that a row added, removed,
 *  reworded or re-dressed on one side shows on the other */
type RowShape = { cls: string[]; label: string | null; sub: string | null; title: string; role: string | null; icon: string | null; swatches: number; ring: number; ariaDisabled: string | null; text: string };
function shape(menu: FakeEl): RowShape[] {
  return menu.children.filter((c) => c.tag !== "#text").map((c) => ({
    cls: c.className.split(/\s+/).filter(Boolean).sort(), label: c.label() ?? null, sub: c.sub() ?? null, title: c.title, role: c.getAttribute("role"),
    icon: c.icon() ? c.icon()!.dataset.kind + (c.icon()!.has("off") ? " off" : "") : null,
    swatches: c.has("ctx-colors") ? c.children.length : 0, ring: c.has("ctx-colors") ? c.children.findIndex((s) => s.has("sel")) : -1,   // the current colour's ringed swatch
    ariaDisabled: c.getAttribute("aria-disabled"), text: c.textContent }));   // the one disabled state the menu has (the Tags flyout's Move to rows under the tab lock)
}
/** the Tags flyout of an open menu, opened by the click the user makes on the Tags row (wireFlyout), and its rows' shape */
function flyShape(menu: FakeEl): RowShape[] {
  menu.children.find((c) => c.has("ctx-item-tags"))!.click();
  const fly = menu.querySelector(".ctx-sub-tags");
  assert.ok(fly, "the Tags flyout opened on the click");
  return shape(fly!);
}
const menuLabel = (r: RowShape) => r.label ?? (r.swatches ? `<${r.swatches} colour swatches>` : r.cls.includes("ctx-sep") ? "<divider>" : `<${r.cls.join(".")}>`);
/** the rows of the row's menu against the tab's, the failure naming the first row that differs by its label (the reviewer's ask): a
 *  row the tab's menu has and the row's lacks, one the row's has and the tab's lacks, or the same row worded or dressed apart */
function sameRows(fromRow: RowShape[], fromTab: RowShape[], where: string) {
  const a = fromRow.map(menuLabel), b = fromTab.map(menuLabel);
  let msg = `${where}: `;
  const i = a.findIndex((l, k) => l !== b[k]);
  if (i >= 0 || a.length !== b.length) {
    const at = i >= 0 ? i : Math.min(a.length, b.length);
    // a row the row's menu lacks: the tab menu's tail after it is the row's menu's tail here; an extra row: the reverse; else the
    // row is another (a swapped pair reads as that, the honest message); the tails decide, since labels repeat (the dividers)
    const same = (x: string[], y: string[]) => x.length === y.length && x.every((l, k) => l === y[k]);
    msg += same(a.slice(at), b.slice(at + 1)) ? `the row's menu lacks the tab menu's row ${at + 1}, ${b[at]}`
         : same(a.slice(at + 1), b.slice(at)) ? `the row's menu has an extra row ${at + 1}, ${a[at]}, that the tab menu lacks`
         : `row ${at + 1} of the row's menu is ${a[at]} where the tab menu's is ${b[at]}`;
  } else {
    const j = fromRow.findIndex((r, k) => JSON.stringify(r) !== JSON.stringify(fromTab[k]));
    msg += j >= 0 ? `row ${j + 1}, ${a[j]}, is worded or dressed apart from the tab menu's` : "the rows agree";
  }
  assert.deepEqual(fromRow, fromTab, msg);
}

test("the fake DOM's nodes enumerate their primitives alone (ui/test-dom-shim.ts): a failing assertion dumps a node, never the tree", () => {
  const n = new FakeEl("div", "snap-item"); const kid = n.appendChild(new FakeEl("button", "snap-row"));
  assert.ok(Object.keys(n).every((k) => staysEnumerable((n as any)[k])), "every enumerable key holds a primitive: " + Object.keys(n).join(","));
  assert.ok(!Object.keys(n).includes("children") && !Object.keys(kid).includes("parent"), "the edges are hidden");
  assert.equal(kid.parent, n); assert.equal(n.children[0], kid);
});

test("executed: a right-click on a HIDDEN session's row opens the tab menu for it, built by showTabMenu with the section as the copy: the same rows, words, dress and states as the strip's own call for that session's copy; a shown row the same; and a call with no copy differs, so the copy the view passes is what makes the rows the tab's", () => withStore(() => {
  const { H, api, host } = world();
  const hidden = host.querySelector(".snap-hidden-list .snap-item[data-id=\"api\"]");
  assert.ok(hidden, "api is hidden in infra: its row sits under the Hidden fold");
  const btn = rowOf(host, "api");
  const ev = rightClick(host, btn.children[1]);   // the pointer lands on a part of the row (the name), and the listener finds the row's item
  assert.ok(ev.prevented && ev.stopped, "the engine's own menu is suppressed and the event stops at the host, as at a tab (the #content listener would put the selection menu up)");
  const fromRow = api.get().ctxMenuEl;
  assert.ok(fromRow && fromRow.isConnected && fromRow.has("ctx-menu"), "the tab menu's card is on the page");
  assert.deepEqual(api.get().ctxMenuAt, { x: 40, y: 300 }, "seated at the pointer");
  const rowShape = shape(fromRow!);
  assert.ok(rowShape.length > 8, "a full menu: " + rowShape.map(menuLabel).join(" | "));
  api.dismiss();
  assert.equal(api.get().ctxMenuEl, null);
  // the strip's call: the tab's handler passes the tab's dataset.copy, the section the copy sits in
  const fromTab = api.showTabMenu({ clientX: 40, clientY: 300 }, "api", "infra");
  const tabShape = shape(fromTab!);
  api.dismiss();
  sameRows(rowShape, tabShape, "api, hidden in infra");
  // THE FLYOUT TOO (the review: the one disabled state the menu has is the Tags flyout's Move to rows under the tab lock, and a flyout
  // is built on the click): opened on both menus by the Tags row's click, its rows equal; under the lock, the Move to row on both sides
  // carries the locked dress and aria-disabled
  rightClick(host, btn);
  const rowFly = flyShape(api.get().ctxMenuEl!);
  api.dismiss();
  const tabFly = flyShape(api.showTabMenu({ clientX: 40, clientY: 300 }, "api", "infra")!);
  api.dismiss();
  sameRows(rowFly, tabFly, "api's Tags flyout");
  assert.deepEqual(rowFly.filter((r) => r.label === "infra" || r.label === "qa").length, 2, "api's own two tags are rows of its flyout: " + rowFly.map(menuLabel).join(" | "));
  assert.ok(rowFly.some((r) => r.label === "Show when folded"), "the pin row too");
  assert.ok(rowFly.every((r) => r.ariaDisabled === null), "nothing disabled while the tabs are unlocked");
  // the lock: web is in infra alone, so its flyout offers Move to qa, the row the lock disables (ctx-item-locked, aria-disabled) on both sides
  api.set({ tabsLocked: true });
  rightClick(host, rowOf(host, "web"), 60, 120);
  const lockedRow = flyShape(api.get().ctxMenuEl!);
  api.dismiss();
  const lockedTab = flyShape(api.showTabMenu({ clientX: 60, clientY: 120 }, "web", "infra")!);
  api.dismiss();
  sameRows(lockedRow, lockedTab, "web's Tags flyout under the tab lock");
  const moveTo = lockedRow.find((r) => r.label?.startsWith("Move to"));
  assert.deepEqual([moveTo?.label, moveTo?.ariaDisabled, moveTo?.cls.includes("ctx-item-locked")], ["Move to qa", "true", true], "the Move to row is disabled on both sides: " + JSON.stringify(moveTo));
  api.set({ tabsLocked: false });
  const hideRow = rowShape.find((r) => r.cls.includes("ctx-item-hide"));
  assert.deepEqual([hideRow?.label, hideRow?.sub, hideRow?.icon], ["Show tab", "back on the strip in infra", "tab off"], "the Hide tab row reads the hidden copy's state");
  // a call with NO copy: api is under two tags, so the menu cannot tell which copy and has no Hide tab row: the shapes differ, and
  // the message names the row
  const noCopy = shape(api.showTabMenu({ clientX: 40, clientY: 300 }, "api")!);
  api.dismiss();
  assert.notDeepEqual(rowShape, noCopy, "the view's copy is what the rows depend on");
  let thrown = "";
  try { sameRows(rowShape, noCopy, "probe"); } catch (e) { thrown = String((e as Error).message); }
  assert.match(thrown, /^probe: the row's menu has an extra row \d+, Show tab, that the tab menu lacks/, "the failure names the row by its label; got: " + thrown.split("\n")[0]);
  // a SHOWN row (web, in infra, one holder): the same equality
  const webBtn = rowOf(host, "web");
  rightClick(host, webBtn, 60, 120);
  const webRow = shape(api.get().ctxMenuEl!);
  api.dismiss();
  const webTab = shape(api.showTabMenu({ clientX: 60, clientY: 120 }, "web", "infra")!);
  api.dismiss();
  sameRows(webRow, webTab, "web, shown in infra");
  assert.equal(webRow.find((r) => r.cls.includes("ctx-item-hide"))?.label, "Hide tab");
  assert.equal(webRow.find((r) => r.label === "Browse files")?.sub, "the session's working tree, in the Files pane", "the web-only row is built for both (the page is served over https here)");
  assert.deepEqual([H.writes.length, H.posts.length, H.flags.length], [0, 0, 0], "opening writes nothing");
  // THE SECTION SHOWN, NOT THE HIDE'S SECTION (the review): api is hidden in infra and shown in qa; the qa view's row speaks for the qa
  // copy, whose Hide tab row hides, and differs from the infra copy's menu, whose row shows
  const q = world({ view: "qa" });
  rightClick(q.host, rowOf(q.host, "api"), 40, 300);
  const qaRow = shape(q.api.get().ctxMenuEl!);
  q.api.dismiss();
  const qaTab = shape(q.api.showTabMenu({ clientX: 40, clientY: 300 }, "api", "qa")!);
  q.api.dismiss();
  sameRows(qaRow, qaTab, "api, shown in qa");
  const qaHide = qaRow.find((r) => r.cls.includes("ctx-item-hide"));
  assert.deepEqual([qaHide?.label, qaHide?.sub, qaHide?.icon], ["Hide tab", "hidden in qa; to show it, open the group's view", "tab"]);
  const infraCopy = shape(q.api.showTabMenu({ clientX: 40, clientY: 300 }, "api", "infra")!);
  q.api.dismiss();
  assert.notDeepEqual(qaRow, infraCopy, "the infra copy's menu (Show tab) is not the qa view's");
}));

test("executed: Show tab on the hidden row's menu writes the show for THAT section and dismisses; the view's next paint moves the row out of the fold", () => withStore(() => {
  const { H, api, host } = world();
  rightClick(host, rowOf(host, "api"));
  const menu = api.get().ctxMenuEl!;
  const row = menu.children.find((c) => c.has("ctx-item-hide"))!;
  assert.equal(row.label(), "Show tab");
  const d0 = H.dismissed;
  row.click();
  assert.equal(H.dismissed, d0 + 1, "the click dismisses the menu");
  assert.equal(H.writes.length, 1);
  assert.equal(isHidden(H.writes[0], INFRA, "api"), false, "api shown in infra again");
  assert.deepEqual(H.writes[0].hidden, [], "no other hide touched");
  // the strip's repaint follows the store event; here the plan is rebuilt from the store and the view painted again
  const unions = viewTagUnion(V);
  const plan = planStrip(IDS, unions, readTabGroups(unions), "web", false);
  api.set({ lastStripItems: plan.items });
  assert.equal(api.renderSnapshot(), true);
  assert.ok(!host.querySelector(".snap-hidden-list .snap-item[data-id=\"api\"]") && host.querySelector(":scope > .snap-list > .snap-item[data-id=\"api\"]"), "api's row is among the shown rows");
}));

test("executed: no menu where the strip has none. A subagent viewer's row and a placeholder's row open nothing and leave the engine's own menu; a skeleton's row opens it; the heading, the fold's head and the host's own gaps open nothing", () => withStore(() => {
  const { api, host } = world({ sub: ["tests"], placeholder: ["web"] });
  const testsEv = rightClick(host, rowOf(host, "tests"));
  assert.equal(api.get().ctxMenuEl, null, "a viewer is read-only: its tab has no menu, so its row has none");
  assert.ok(!testsEv.prevented && !testsEv.stopped, "the engine's own menu stands where ours does not open");
  assert.ok(rowOf(host, "web").has("loading"), "web has no frame: a loading row");
  rightClick(host, rowOf(host, "web"));
  assert.equal(api.get().ctxMenuEl, null, "a placeholder tab (the kernel still building the session) has no menu");
  const headEv = rightClick(host, host.querySelector(".snap-head")!);
  const foldEv = rightClick(host, host.querySelector(".snap-hidden-head")!);
  const gapEv = rightClick(host, host);
  assert.equal(api.get().ctxMenuEl, null);
  assert.ok(!headEv.prevented && !foldEv.prevented && !gapEv.prevented, "the heading, the fold's head and the gaps are not rows");
  // a skeleton (the session resting, loads on a click): its tab carries the menu (makeSkeletonTab), so its row does too
  const sk = world({ placeholder: ["web"], skeleton: ["web"] });
  rightClick(sk.host, rowOf(sk.host, "web"));
  assert.ok(sk.api.get().ctxMenuEl, "a skeleton's row opens the menu");
  assert.equal(shape(sk.api.get().ctxMenuEl!).find((r) => r.label === "Rename")?.label, "Rename");
  sk.api.dismiss();
}));

test("executed: the keyboard's contextmenu carries no place (clientX and clientY at 0) and seats the menu at the row's bottom-left corner; a pointer's event opens where it is (menuAnchor)", () => withStore(() => {
  const { api, host } = world();
  const btn = rowOf(host, "api");
  btn.rect = { left: 30, top: 200, right: 500, bottom: 230, width: 470, height: 30 };
  btn.focus();
  rightClick(host, btn, 0, 0);
  assert.ok(api.get().ctxMenuEl, "the menu opens from the keyboard");
  assert.deepEqual(api.get().ctxMenuAt, { x: 30, y: 230 }, "at the row's corner, not the pane's");
  api.dismiss();
  rightClick(host, btn, 77, 333);
  assert.deepEqual(api.get().ctxMenuAt, { x: 77, y: 333 }, "a pointer's event opens at the pointer");
  api.dismiss();
  // the helper, pure
  const e = { clientX: 5, clientY: 9 };
  assert.equal(menuAnchor(e, () => { throw new Error("the rect is not read when the event carries a place"); }), e, "the event itself comes back");
  assert.deepEqual(menuAnchor({ clientX: 0, clientY: 0 }, () => ({ left: 12, bottom: 40 })), { clientX: 12, clientY: 40 });
  assert.deepEqual(menuAnchor({ clientX: 0, clientY: 3 }, () => ({ left: 12, bottom: 40 })), { clientX: 0, clientY: 3 }, "one non-zero coordinate is a place");
}));

test("executed: Rename from the hidden row's menu edits the name ON THE ROW: the input stands where the row's button was, a push while editing is held and flushed at the end, Enter posts renameSession with the new name and hands the focus back to the row; Escape posts nothing; a blur commits", () => withStore(() => {
  const { H, api, host, bar } = world();
  openFold(H, host);   // the hidden row is right-clickable only while its fold is open
  const item = itemOf(host, "api"), btn = rowOf(host, "api");
  rightClick(host, btn);
  const rename = api.get().ctxMenuEl!.children.find((c) => c.label() === "Rename")!;
  assert.equal(rename.sub(), RENAME_SUBLINE);
  rename.click();   // the builder's row: the menu closes, then the pick runs startTabRename(id, copy)
  assert.equal(api.get().ctxMenuEl, null);
  const input = item.querySelector(":scope > .tab-rename")!;
  assert.ok(input, "the strip's editor, in the row's item");
  assert.deepEqual(item.children.map((c) => c.className.split(" ")[0]), ["snap-row", "tab-rename", "snap-act"], "after the row's button, before the Hide or Show button");
  assert.deepEqual([btn.style.display, input.value, input.tag, FOCUS === input, api.get().renameActive], ["none", "api", "input", true, true], "the button hidden, the name in the field, focused, the hold taken");
  assert.equal(bar.querySelector(".tab-rename"), null, "no editor on the strip's tab: the row's menu edits the row");
  // a push while editing: the model changes (api's summary), the view is NOT repainted and the flush is armed
  H.ledgers.set("api", { summary: "Writing the notes schema", needsInput: false, tree: [] });
  assert.equal(api.renderSnapshot(), true);
  assert.deepEqual([api.get().renderPendingAfterRename, item.querySelector(":scope > .tab-rename") === input, btn.style.display, btn.querySelector(".snap-now")!.textContent],
                   [true, true, "none", "Designing the notes schema"], "held: the input stands, the row's parts are not rewritten under it");
  // Enter with a new name: the post, the row back, the focus on the row, the flush painted the new summary
  input.value = "api2";
  input.fire("keydown", { key: "Enter", preventDefault() {}, stopPropagation() {} });
  assert.deepEqual(H.posts, [{ type: "renameSession", id: "api", name: "api2" }]);
  assert.deepEqual([item.querySelector(":scope > .tab-rename"), btn.style.display, FOCUS === btn, api.get().renameActive, api.get().renderPendingAfterRename], [null, "", true, false, false]);
  assert.equal(btn.querySelector(".snap-now")!.textContent, "Writing the notes schema", "the held push painted at the end");
  // Escape: nothing posted, the row back
  rightClick(host, btn);
  api.get().ctxMenuEl!.children.find((c) => c.label() === "Rename")!.click();
  const input2 = item.querySelector(":scope > .tab-rename")!;
  input2.value = "never";
  input2.fire("keydown", { key: "Escape", preventDefault() {}, stopPropagation() {} });
  assert.equal(H.posts.length, 1, "Escape posts nothing");
  assert.deepEqual([item.querySelector(":scope > .tab-rename"), btn.style.display, api.get().renameActive], [null, "", false]);
  // an unchanged name commits nothing; a blur commits a changed one
  rightClick(host, btn);
  api.get().ctxMenuEl!.children.find((c) => c.label() === "Rename")!.click();
  const input3 = item.querySelector(":scope > .tab-rename")!;
  input3.fire("blur");
  assert.equal(H.posts.length, 1, "the same name: nothing to post");
  rightClick(host, btn);
  api.get().ctxMenuEl!.children.find((c) => c.label() === "Rename")!.click();
  const input4 = item.querySelector(":scope > .tab-rename")!;
  input4.value = "api3"; FOCUS = BODY;   // the focus moved elsewhere first (a click outside), then the blur
  input4.fire("blur");
  assert.deepEqual(H.posts[1], { type: "renameSession", id: "api", name: "api3" });
  assert.equal(FOCUS, BODY, "a blur that moved the focus elsewhere moves nothing back");
}));

test("executed: a REMOTE row's Rename (round 1 of the review, 2026-09-18): the host prefix stands as the strip's fixed span between the row's button and the input, the field is seeded with the bare name, and the post carries the bare name, never the prefix", () => withStore(() => {
  // the remote is a shown member of infra: its row is in the shown list, no fold to open
  const { H, api, host, bar } = world();
  const item = itemOf(host, REMOTE), btn = rowOf(host, REMOTE);
  assert.ok(item && btn && !item.closest(".snap-hidden-list"), "the remote's row is a shown row of the infra view");
  assert.ok(bar.querySelector(`.tab[data-id="${REMOTE}"]`), "…and it has a tab on the strip too (the row's menu edits the row all the same)");
  rightClick(host, btn);
  const rename = api.get().ctxMenuEl!.children.find((c) => c.label() === "Rename")!;
  assert.ok(rename, "the remote row's menu has Rename");
  rename.click();
  // the order the sheet's two host-prefix rules dress (.snap-item > .host-prefix, .snap-item > .host-prefix + .tab-rename): the prefix
  // is a child of the item, before the input; a reseat that dropped it, or put it inside the button, would fail here
  assert.deepEqual(item.children.map((c) => c.className.split(" ")[0]), ["snap-row", "host-prefix", "tab-rename", "snap-act"], "the row's button, the fixed prefix, the input, the Hide button");
  const fixed = item.children[1], input = item.querySelector(":scope > .tab-rename")!;
  assert.deepEqual([fixed.textContent, input.value, btn.style.display, FOCUS === input, api.get().renameActive], ["TESTHOST:", "remote", "none", true, true],
                   "the prefix as the far side prepended it, the BARE name in the field, the button hidden, the focus taken, the hold on");
  assert.equal(bar.querySelector(".tab-rename"), null, "no editor on the strip's tab: the row's menu edits the row");
  input.value = "remote2";
  input.fire("keydown", { key: "Enter", preventDefault() {}, stopPropagation() {} });
  assert.deepEqual(H.posts, [{ type: "renameSession", id: REMOTE, name: "remote2" }], "the prefixed id (federation routes on it) and the bare name (the far kernel knows no prefix)");
  assert.deepEqual([item.children.map((c) => c.className.split(" ")[0]), btn.style.display, FOCUS === btn, api.get().renameActive], [["snap-row", "snap-act"], "", true, false],
                   "the prefix span leaves with the input; the row back, focused, the hold released");
}));

test("executed: THE SEAT FOLLOWS THE MENU (review round 1). With the view up on infra and web's row shown, a Rename from web's TAB menu edits the tab, not the row; api hidden in infra with the fold CLOSED and a tab under qa: a Rename from that tab edits the tab (the row is not rendered), and a row seat asked for anyway falls to the tab; api under infra alone, hidden, fold closed: no editor and no hold; a seat whose focus the engine refuses is undone and takes no hold", () => withStore(() => {
  // 1. the tab's menu while the view shows the session's row: the TAB's editor (a row-first rule moved it into the pane)
  const w = world({ hide: false });
  assert.ok(rowOf(w.host, "web"), "web has a row in the infra view");
  w.api.showTabMenu({ clientX: 40, clientY: 30 }, "web", "infra");
  assert.equal(w.api.get().tabMenuSeat, "tab", "a tab opened it");
  w.api.get().ctxMenuEl!.children.find((c) => c.label() === "Rename")!.click();
  const webTab = w.bar.querySelector(".tab[data-id=\"web\"]")!;
  assert.ok(webTab.querySelector(".tab-rename"), "the editor on web's tab");
  assert.equal(w.host.querySelector(".tab-rename"), null, "none on the row");
  assert.deepEqual([webTab.querySelector(".tab-label")!.style.display, rowOf(w.host, "web").style.display, w.api.get().renameActive], ["none", "", true]);
  webTab.querySelector(".tab-rename")!.fire("keydown", { key: "Escape", preventDefault() {}, stopPropagation() {} });
  assert.equal(w.api.get().renameActive, false);
  // 2. the high finding's scenario: api hidden in infra (the fold closed, the default), the infra view up, api's qa tab on the strip
  const c = world();
  assert.equal(c.host.querySelector(".snap-hidden-list")!.style.display, "none", "the fold is closed");
  assert.ok(c.host.querySelector(".snap-hidden-list .snap-item[data-id=\"api\"]"), "api's row stands in the folded list, unrendered");
  const qaTab = c.bar.querySelectorAll(".tab[data-id=\"api\"]").find((t) => t.dataset.copy === "qa")!;
  assert.ok(qaTab, "api's tab under qa");
  c.api.showTabMenu({ clientX: 40, clientY: 30 }, "api", "qa");
  c.api.get().ctxMenuEl!.children.find((c2) => c2.label() === "Rename")!.click();
  assert.ok(qaTab.querySelector(".tab-rename"), "the editor on the qa tab");
  assert.equal(c.host.querySelector(".tab-rename"), null, "nothing in the folded list");
  assert.deepEqual([c.api.get().renameActive, FOCUS === qaTab.querySelector(".tab-rename")], [true, true], "the hold, for an editor that has the focus");
  qaTab.querySelector(".tab-rename")!.fire("keydown", { key: "Escape", preventDefault() {}, stopPropagation() {} });
  assert.equal(c.api.get().renameActive, false);
  // a row seat asked for with the fold closed (the listener cannot be reached, but the guard is executed): the tab
  c.api.set({ tabMenuSeat: "row" });
  c.api.startTabRename("api", "infra");
  assert.ok(c.bar.querySelector(".tab[data-id=\"api\"] .tab-rename"), "rowSeatFor says null under a closed fold: the tab path");
  assert.equal(c.host.querySelector(".tab-rename"), null);
  c.bar.querySelector(".tab-rename")!.fire("keydown", { key: "Escape", preventDefault() {}, stopPropagation() {} });
  // 3. api under infra alone, hidden, fold closed: no tab anywhere and no rendered row: no editor, no hold (the bail-out precedes the flag)
  const s = world({ single: true });
  assert.equal(s.bar.querySelector(".tab[data-id=\"api\"]"), null, "no tab: hidden in its only group");
  s.api.set({ tabMenuSeat: "row" });
  s.api.startTabRename("api", "infra");
  assert.deepEqual([s.api.get().renameActive, s.host.querySelector(".tab-rename"), s.H.posts.length], [false, null, 0]);
  // 4. the fold open (the row rendered, so the seat is the row), then the engine refuses the focus (here: the list hidden under an open fold
  // state, an inconsistency the fake permits): the seat is undone, no hold
  openFold(s.H, s.host);
  s.host.querySelector(".snap-hidden-list")!.style.display = "none";
  s.api.startTabRename("api", "infra");
  const sItem = itemOf(s.host, "api");
  assert.deepEqual([s.api.get().renameActive, sItem.querySelector(".tab-rename"), rowOf(s.host, "api").style.display, s.api.get().rowRenameEnd], [false, null, "", false], "undone: the button back, nothing held");
  s.host.querySelector(".snap-hidden-list")!.style.display = "";
  s.api.startTabRename("api", "infra");
  assert.deepEqual([s.api.get().renameActive, !!sItem.querySelector(".tab-rename"), s.api.get().rowRenameEnd], [true, true, true], "rendered again: the row's editor, its end registered");
  sItem.querySelector(".tab-rename")!.fire("keydown", { key: "Escape", preventDefault() {}, stopPropagation() {} });
  assert.equal(s.api.get().rowRenameEnd, false, "the end is cleared with the editor");
}));

test("executed: THE VIEW LEAVES UNDER A ROW EDITOR (review round 1): the exit (hideSnapshot, which every exit runs) ends the edit as a click away does, a commit; the hold is released, the deferred strip render flushes a tick later (the release idiom), the row takes no focus back", async () => {
  const store = new Map<string, string>(); const g: any = globalThis; const saved = g.localStorage;
  g.localStorage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => { store.set(k, v); }, removeItem: (k: string) => { store.delete(k); } };
  try {
    const { H, api, host } = world();
    openFold(H, host);
    const item = itemOf(host, "api"), btn = rowOf(host, "api");
    rightClick(host, btn);
    api.get().ctxMenuEl!.children.find((c) => c.label() === "Rename")!.click();
    const input = item.querySelector(":scope > .tab-rename")!;
    assert.ok(input && api.get().rowRenameEnd, "the row's editor, its end registered");
    H.ledgers.set("api", { summary: "Writing the notes schema", needsInput: false, tree: [] });
    assert.equal(api.renderSnapshot(), true);
    assert.deepEqual([api.get().renderPendingAfterRename, host.style.display], [true, ""], "held, and the gate leaves the host shown");
    input.value = "api9";
    const r0 = H.renders;
    // a chord or a host message switched the session: setActive clears snapView and showActive hides the view (hideSnapshot)
    api.set({ snapView: null });
    api.hideSnapshot();
    assert.deepEqual([item.querySelector(":scope > .tab-rename"), btn.style.display, api.get().renameActive, api.get().rowRenameEnd, host.style.display], [null, "", false, false, "none"], "the editor ended and the host hid");
    assert.deepEqual(H.posts, [{ type: "renameSession", id: "api", name: "api9" }], "committed, as a click away commits");
    assert.notEqual(FOCUS, btn, "no focus back onto a row about to hide");
    assert.equal(H.renders, r0, "the flush is not synchronous inside the exit");
    await new Promise((r) => setTimeout(r, 5));
    assert.equal(H.renders, r0 + 1, "…it ran a tick later, the release idiom");
    assert.equal(api.get().renderPendingAfterRename, false);
  } finally { g.localStorage = saved; }
});

test("executed: with the view closed, Rename edits the tab's label on the strip as before; with the view up on a section the session has no row in, the tab too; a session gone from both surfaces takes no hold", () => withStore(() => {
  const { H, api, host, bar } = world({ hide: false, view: null });
  assert.equal(host, null, "no view painted");
  api.startTabRename("web", "infra");
  const tab = bar.querySelector(".tab[data-id=\"web\"]")!, label = tab.querySelector(".tab-label")!, input = tab.querySelector(".tab-rename")!;
  assert.ok(input && label.style.display === "none" && tab.children.indexOf(input) === tab.children.indexOf(label) + 1, "the input after the hidden label, on the tab");
  assert.deepEqual([tab.draggable, api.get().renameActive], [false, true]);
  input.value = "web2";
  input.fire("keydown", { key: "Enter", preventDefault() {}, stopPropagation() {} });
  assert.deepEqual([H.posts, label.style.display, tab.querySelector(".tab-rename"), api.get().renameActive], [[{ type: "renameSession", id: "web", name: "web2" }], "", null, false]);
  // the view up on qa (api and tests): web has no row there, so its Rename edits the tab
  const w2 = world({ hide: false, view: "qa" });
  assert.ok(w2.host.querySelector(".snap-item[data-id=\"api\"]") && !w2.host.querySelector(".snap-item[data-id=\"web\"]"));
  w2.api.startTabRename("web", "infra");
  assert.ok(w2.bar.querySelector(".tab[data-id=\"web\"] .tab-rename"), "the tab's editor");
  assert.equal(w2.host.querySelector(".tab-rename"), null);
  w2.bar.querySelector(".tab-rename")!.fire("keydown", { key: "Escape", preventDefault() {}, stopPropagation() {} });
  // a session on neither surface (its tab gone, no row): no editor, no hold (the clicksafe rule: the bail-out precedes the flag)
  const w3 = world({ hide: false, view: null });
  w3.bar.querySelector(".tab[data-id=\"web\"]")!.remove();
  w3.api.startTabRename("web", "infra");
  assert.deepEqual([w3.api.get().renameActive, w3.H.posts.length], [false, 0]);
}));

test("source: the strip's two wirings and the view's one call the same builder; the host's listener is one, click-safe, gated as the strip's tabs are, and stops the event; the view's rebuild honours the rename hold; the anchor is the shared helper", () => {
  const wiring = 'tab.addEventListener("contextmenu", (e) => { e.preventDefault(); e.stopPropagation(); showTabMenu(e, id, tab.dataset.copy); });';
  assert.equal(RENDER.split(wiring).length - 1, 2, "the loaded tab's and the skeleton's wirings pass the tab's copy");
  const snap = SNAP;
  assert.equal(snap.split('host.addEventListener("contextmenu", (e) => {').length - 1, 1, "one listener, on the stable host");
  assert.match(snap, /const item = \(e\.target as HTMLElement \| null\)\?\.closest\?\.\("\.snap-item"\) as HTMLElement \| null;/, "the row's item, from wherever in it the pointer landed");
  assert.match(snap, /if \(!item \|\| !id \|\| !snapView \|\| !rowHasTabMenu\(id\)\) return;/, "the gate, before the default is touched");
  assert.match(snap, /e\.preventDefault\(\); e\.stopPropagation\(\);\n\s+const row = item\.querySelector<HTMLElement>\(":scope > \.snap-row"\) \?\? item;\n\s+showTabMenu\(menuAnchor\(e, \(\) => row\.getBoundingClientRect\(\)\) as MouseEvent, id, snapView\);/, "the same builder, the section as the copy, the anchored event");
  assert.match(snap, /function rowHasTabMenu\(id: string\): boolean \{\n\s+const s = sessions\.get\(id\);\n\s+if \(renderKind\(skeletonTabs, id, !!s\) === "skeleton"\) return true;\n\s+return !!s && !s\.sub;\n\}/, "the strip's gate: a skeleton, or a loaded session that is no viewer");
  assert.match(RENDER, /if \(renderKind\(skeletonTabs, id, !!s\) === "skeleton"\) \{\n\s+const sk = makeSkeletonTab\(id\);/, "…as renderTabs paints a skeleton (with the menu)");
  assert.match(RENDER, /if \(!s\.sub\) tab\.addEventListener\("contextmenu"/, "…and wires a loaded tab's menu for no viewer");
  assert.match(snap, /if \(tabPointerHeld && host\.childElementCount\) \{ renderPendingWhilePressed = true; return true; \}\n(\s+\/\/[^\n]*\n)+\s+if \(renameActive && host\.childElementCount\) \{ renderPendingAfterRename = true; host\.style\.display = ""; return true; \}[^\n]*\n\s+snapModel = next;/, "the rename hold, after the press hold, before the rebuild; a true answer shows the host");
  assert.match(RENDER, /import \{ rowStillOpen, installSnapshotEscape, reconcileRows, repeatedClick, menuAnchor \} from "\.\/tab-snapshot-view";/);
  assert.equal(RENDER.split("menuAnchor(").length - 1, 1, "one caller: the host's listener");
  // startTabRename: the row first, resolved now, by id; the tab only when there is no row; the bail-out still precedes the flag
  assert.match(RENAME, /const row = tabMenuSeat === "row" \? rowSeatFor\(id\) : null;\n\s+const item = row \? row\.parentElement : null;/, "the seat follows the menu; the row only when rendered (rowSeatFor)");
  assert.match(SNAP, /function rowSeatFor\(id: string\): HTMLElement \| null \{\n\s+const host = document\.getElementById\("tab-snapshot"\);\n\s+if \(!snapView \|\| !host \|\| host\.style\.display === "none"\) return null;\n\s+const item = host\.querySelector<HTMLElement>\(`\.snap-item\[data-id="\$\{cssEscape\(id\)\}"\]`\);\n\s+if \(!item \|\| \(item\.closest\("\.snap-hidden-list"\) && !snapHiddenOpen\.has\(snapView\)\)\) return null;/, "the view up, the row shown or its fold open");
  assert.equal(MENU.split('tabMenuSeat = "tab";').length - 1, 1, "showTabMenu names the tab at every open");
  assert.match(SNAP, /showTabMenu\(menuAnchor\(e, \(\) => row\.getBoundingClientRect\(\)\) as MouseEvent, id, snapView\);\n\s+tabMenuSeat = "row";/, "the view's listener names the row once the menu is built");
  assert.match(SNAP, /function hideSnapshot\(\): void \{\n\s+if \(rowRenameEnd\) rowRenameEnd\(true, true\);/, "the exit ends a row editor before the host hides");
  assert.match(RENAME, /input\.focus\(\);\n(\s+\/\/[^\n]*\n)+\s+if \(document\.activeElement !== input\) \{ unseat\(\); return; \}\n\s+input\.select\(\);\n\s+renameActive = true;\n\s+if \(row\) rowRenameEnd = done;/, "the hold only once the focus took");
  assert.match(RENAME, /if \(renderPendingAfterRename\) \{ renderPendingAfterRename = false; if \(viewLeft\) setTimeout\(\(\) => renderTabs\(\), 0\); else renderTabs\(\); \}/, "the exit's flush is deferred, the release idiom");
  assert.doesNotMatch(RENAME, /the user 2026-08-08: "/, "the user is paraphrased, never quoted (the privacy rule)");
  assert.match(RENAME, /const bar = row \? null : document\.getElementById\("tabs"\);/);
  assert.match(RENAME, /if \(row\) \{ if \(item!\.querySelector\("\.tab-rename"\)\) return; \}[^\n]*\n\s+else if \(!tab \|\| !label \|\| tab\.querySelector\("\.tab-rename"\)\) return;\n\s+const seat = \(row \?\? label\)!;/);
  assert.ok(RENAME.indexOf("const seat = ") < RENAME.indexOf("renameActive = true"), "the bail-out precedes the flag on both surfaces");
  assert.match(RENAME, /if \(row && hadFocus && row\.isConnected && !viewLeft\) row\.focus\(\{ preventScroll: true \}\);/, "the row takes the focus back, except as the view leaves");
});

test("the sheet: the row's editor rule, tokens and metrics only; the docs: the guide's overview and hidden paragraphs and the reference say the row's right-click opens the tab's menu, no em dash", () => {
  const block = CSS.slice(CSS.indexOf("/* THE ROW'S RENAME"), CSS.indexOf(".snap-act {"));
  assert.ok(block.length > 100, "the rule sits with the item's rules");
  // the auto right margin (round 1 of the review, 2026-09-18): the free space the field leaves goes between the field and the Hide or
  // Show button, which keeps the row's right edge; tests/test_tab_snapshot_menu_served.py measures it on the served page
  assert.match(block, /\.snap-item > \.tab-rename \{ flex: 0 1 auto; margin: 4px auto 0 8px; \}/);
  assert.match(block, /\.snap-item > \.host-prefix \{ margin: 5px 0 0 8px; \}/);
  assert.doesNotMatch(block, /#[0-9a-fA-F]{3,8}\b|rgba?\(/, "no colour of its own: the strip's input carries the dress");
  // THE PARAGRAPHS THEMSELVES (round 1 of the review, 2026-09-18): the two guide paragraphs the change edited, sliced out of the guide
  // between markers that must both stand (tab-hide.test.ts's idiom), so the em-dash and vocabulary check below reads the guide's
  // text and not a literal of this file's, which could never fail. ONE PARAGRAPH EACH (round 2 of the review): a slice ends at the
  // NEXT paragraph's bold opener, never at the section's heading, and is held to one paragraph and to a ceiling on its length. The
  // hidden slice had run to the feed heading, 9,354 chars over four paragraphs, three of them never edited by this change, and the
  // minimum alone let that pass: an em dash written into one of those three would have turned this test red naming the hidden
  // paragraph. Each ceiling sits under the slice plus the paragraph after it, so a slice that widens by a paragraph fails here
  const guidePara = (from: string, to: string) => { const a = GUIDE.indexOf(from), b = GUIDE.indexOf(to, a + 1); assert.ok(a >= 0 && b > a, `the guide's markers moved: ${from} .. ${to}`); return GUIDE.slice(a, b); };
  const overview = guidePara("**A section at a glance.**", "**Hiding a session inside its group.**");
  const hidden = guidePara("**Hiding a session inside its group.**", "**Coming back after a dropped connection.**");
  for (const [name, s, ceiling] of [["overview", overview, 3000], ["hidden", hidden, 6000]] as const) {
    assert.ok(s.length > 500 && s.length < ceiling, `the guide's ${name} paragraph, whole and alone: ${s.length} chars against a ceiling of ${ceiling}`);
    assert.ok(!s.trimEnd().includes("\n\n"), `the guide's ${name} slice holds a paragraph break: it runs past its paragraph`);
  }
  const flat = (s: string) => s.replace(/\s+/g, " ");
  assert.match(flat(overview), /see the next paragraph\)\. Right-click a row, or press the menu key while the row has the focus, to open the menu a right-click on the session's tab opens, with the same rows\. \*\*Rename\*\* from that menu edits the name on the row while this view shows it\. The rows update as/, "the overview paragraph");
  assert.match(flat(hidden), /A hidden session has no tab to right-click, so this view's \*\*Show\*\* button puts it back\. A right-click on its row here opens the tab's menu, where \*\*Hide tab\*\* reads \*\*Show tab\*\*\./, "the hidden paragraph: two sentences, the menu item named as an item (the review)");
  assert.match(flat(REF), /the way back is the view's \*\*Show\*\*, or the same menu from a right-click on its row there, and the group's count opens the view while the group is open\)/, "the reference");
  for (const [name, s] of [["the sheet's block", block], ["the guide's overview paragraph", overview], ["the guide's hidden paragraph", hidden]] as const) {
    assert.ok(!s.includes("\u2014"), `no em dash in ${name}`);
    assert.ok(!/fleet/i.test(s), `the user's vocabulary in ${name}`);
  }
});
