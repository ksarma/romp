// The Comment offer on a keyboard selection (plans/markdown-viewer.md Slice 5, item 9; file-comments.ts onSelectionChange). The
// float rode one trigger, the seam's mouseup and touchend (file-view.ts onSelect, the panel's onSelection hook), so a selection made
// or changed from the keyboard, Shift+Arrow over a selection a drag began, caret browsing, assistive technology, offered nothing,
// and the float stayed where the drag had left it while the selection shrank under it (the Slice 5 probe (i)). Now the panel hears
// the document's selectionchange itself, with four guards, and then runs the seam's own path: a selectionchange with the selection
// the float is already offered beside does nothing (the seam's re-seat of the same ends after a paint fires the event too, and an
// offer a scroll hid stays hidden); a collapsed selection hides the float; one arriving while a pointer is down does nothing (a
// drag keeps its one offer at mouseup, and the float does not flicker mid-drag); one with an end outside the body hides a passage's
// float and offers nothing, and with the collapsed hide drops the record of the offer, so the selection the keyboard brings back to
// the offered ends is offered again (the Slice 5 review, round 4: Shift+ArrowDown into the aside hid the float, and the Shift+ArrowUp
// after it, back at exactly the ends of the last offer, read as the selection already answered and offered nothing); a DIFFERENT
// non-collapsed selection inside the body shows the float at the new rect; nothing while the
// editor holds the body; and the listeners leave at dispose. The press flag takes pressHold's shape (the Slice 5 review, round 2):
// a right or middle mousedown raises it not at all, since Chromium on Linux and macOS opens the native context menu on that
// mousedown and the menu takes the release, so a flag raised by one stood until the next left click and every keyboard change in
// between offered nothing; a contextmenu and the window's blur end a press as a mouseup does (ctrl+click on macOS and a long press
// on a touch screen end in a contextmenu and no mouseup; a release in another frame never reaches this one). Driven over the
// behavior suite's DOM stand-in with the selection faked
// per case (window.getSelection is what the panel reads) and the document's listeners run as the browser runs them.
// file-comments-keyboard-offer-browser.test.ts presses the keys in Chromium. Nodes hide their edges at construction (hideEdges,
// ui/test-dom-shim.ts). Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
import { hideEdges } from "../test-dom-shim";

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
const QUOTE = "shipping the cache in v1.2";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\nWe recommend " + QUOTE + ".\n\nMore text here.\n";
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: QUOTE, prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
function status(): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] },
    hunks: [], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
  };
}

// ── the DOM stand-in (the behavior suite's): ancestry, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  button: number;   // MouseEvent.button: 0 the primary, 1 the middle, 2 the right (the default a browser gives a MouseEvent)
  detail = 0;
  constructor(public type: string, init: { key?: string; button?: number } = {}) { this.key = init.key || ""; this.button = init.button ?? 0; hideEdges(this); }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Reg = { type: string; cb: Listener; capture: boolean };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) { hideEdges(this); }
  get textContent(): string { return this.data; }
  get length(): number { return this.data.length; }
  get parentElement(): El | null { return this.parentNode; }
  splitText(off: number): Txt {
    const tail = new Txt(this.data.slice(off));
    this.data = this.data.slice(0, off);
    const p = this.parentNode;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Compound = { tag: string | null; classes: string[]; attrs: Array<[string, string | null]> };
function parseSel(sel: string): Compound[][] {
  return sel.split(",").map((g) => g.trim()).filter(Boolean).map((g) => g.split(/\s+/).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?((?:\.[\w-]+)*)((?:\[[\w-]+(?:="[^"]*")?\])*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    const classes = (m[2].match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
    const attrs: Array<[string, string | null]> = [];
    for (const a of m[3].match(/\[[^\]]+\]/g) || []) { const am = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(a)!; attrs.push([am[1], am[2] ?? null]); }
    return { tag: m[1] ? m[1].toUpperCase() : null, classes, attrs };
  }));
}
class El {
  nodeType = 1;
  tagName: string;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; readOnly = false; title = ""; type = ""; value = ""; checked = false; placeholder = "";
  innerHTML = "";
  style: Record<string, string> = {};
  rect = { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
  constructor(tag: string) { this.tagName = tag.toUpperCase(); hideEdges(this); }
  get ownerDocument(): typeof doc { return doc; }
  get parentElement(): El | null { return this.parentNode; }
  get firstChild(): El | Txt | null { return this.childNodes[0] || null; }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  get classes(): string[] { return this.className.split(/\s+/).filter(Boolean); }
  classList = {
    add: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.add(x); this.className = [...s].join(" "); },
    remove: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.delete(x); this.className = [...s].join(" "); },
    toggle: (c: string, on?: boolean) => { const want = on === undefined ? !this.classes.includes(c) : on; if (want) this.classList.add(c); else this.classList.remove(c); },
    contains: (c: string) => this.classes.includes(c),
  };
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : -1; }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  dataset: Record<string, string> = new Proxy({} as Record<string, string>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))) as string,
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
    deleteProperty: (_, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes = []; if (v !== "") this.appendChild(new Txt(v)); }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes = []; for (const x of c) this.appendChild(x); }
  remove(): void { this.detach(this); }
  normalize(): void {
    const out: Array<El | Txt> = [];
    for (const c of this.childNodes) {
      if (c instanceof Txt) { if (!c.data) { c.parentNode = null; continue; } const last = out[out.length - 1]; if (last instanceof Txt) { last.data += c.data; c.parentNode = null; continue; } }
      else c.normalize();
      out.push(c);
    }
    this.childNodes = out;
  }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  getAttribute(k: string): string | null { return this.attrs.has(k) ? (this.attrs.get(k) as string) : null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  contains(n: El | Txt | null): boolean { for (let x: El | Txt | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  private fits(c: Compound): boolean {
    return (!c.tag || c.tag === this.tagName) && c.classes.every((k) => this.classes.includes(k))
      && c.attrs.every(([a, v]) => this.attrs.has(a) && (v === null || this.attrs.get(a) === v));
  }
  matches(sel: string): boolean {
    return parseSel(sel).some((chain) => {
      if (!this.fits(chain[chain.length - 1])) return false;
      let k = chain.length - 2;
      for (let a: El | null = this.parentNode; a && k >= 0; a = a.parentNode) if (a.fits(chain[k])) k--;
      return k < 0;
    });
  }
  closest(sel: string): El | null { for (let x: El | null = this; x; x = x.parentNode) if (x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): El[] {
    const out: El[] = [];
    const visit = (n: El) => { for (const c of n.childNodes) if (c instanceof El) { if (c.matches(sel)) out.push(c); visit(c); } };
    visit(this);
    return out;
  }
  querySelector(sel: string): El | null { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    this.listeners.push({ type, cb, capture: typeof opts === "boolean" ? opts : !!(opts && opts.capture) });
  }
  removeEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    const cap = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    this.listeners = this.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  }
  dispatchEvent(ev: Ev): boolean { return dispatch(this, ev); }
  click(): void { this.dispatchEvent(new Ev("click")); }
  focus(): void { doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  scrollIntoView(): void { /* inert */ }
  getBoundingClientRect(): typeof this.rect { return this.rect; }
  get offsetWidth(): number { return 0; }
}
const doc = hideEdges({
  listeners: [] as Reg[],
  body: null as unknown as El,
  hidden: false,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  getElementById: () => null,
  addEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    doc.listeners.push({ type, cb, capture: typeof opts === "boolean" ? opts : !!(opts && opts.capture) });
  },
  removeEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    const cap = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    doc.listeners = doc.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  },
  contains: (n: El | Txt | null) => doc.body.contains(n),
});
doc.body = new El("body");
/** The DOM event path: document capture, ancestors' capture root to target, target and ancestors' bubble, document bubble. */
function dispatch(target: El | Txt, ev: Ev): boolean {
  ev.target = target;
  const chain: El[] = [];
  for (let n: El | null = target instanceof El ? target : target.parentNode; n; n = n.parentNode) chain.push(n);
  const run = (ls: Reg[], capture: boolean, node: El | null): boolean => {
    for (const l of ls.slice()) {
      if (l.type !== ev.type || l.capture !== capture) continue;
      ev.currentTarget = node; l.cb.call(node, ev);
      if (ev.stopped) return true;
    }
    return false;
  };
  if (run(doc.listeners, true, null)) return !ev.defaultPrevented;
  for (let i = chain.length - 1; i >= 0; i--) if (run(chain[i].listeners, true, chain[i])) return !ev.defaultPrevented;
  for (const n of chain) if (run(n.listeners, false, n)) return !ev.defaultPrevented;
  run(doc.listeners, false, null);
  return !ev.defaultPrevented;
}
/** The document's own event (selectionchange has no target in the tree): its listeners in both phases, as the browser runs them. */
function documentEvent(type: string): void {
  const ev = new Ev(type);
  for (const capture of [true, false]) for (const l of doc.listeners.slice()) if (l.type === type && l.capture === capture) l.cb.call(null, ev);
}
const win: any = new EventTarget();
win.parent = win; win.innerWidth = 1200; win.innerHeight = 800;
/** The window's listeners by type, as installed and removed (a native EventTarget lists none): the press flag's blur release. */
const winListeners: Reg[] = [];
const winAdd = win.addEventListener.bind(win), winRemove = win.removeEventListener.bind(win);
win.addEventListener = (type: string, cb: Listener, opts?: boolean | { capture?: boolean }) => {
  winListeners.push({ type, cb, capture: typeof opts === "boolean" ? opts : !!(opts && opts.capture) }); winAdd(type, cb, opts);
};
win.removeEventListener = (type: string, cb: Listener, opts?: boolean | { capture?: boolean }) => {
  const cap = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
  const i = winListeners.findIndex((l) => l.type === type && l.cb === cb && l.capture === cap); if (i >= 0) winListeners.splice(i, 1);
  winRemove(type, cb, opts);
};
let selection: any = null;
win.getSelection = () => selection;
win.confirm = () => true;
hideEdges(win);
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, the poll's HEAD answers ──
type World = { ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El; actions: El; hooks: { rendered: Array<() => void>; selection: Array<(s: Selection) => void>; close: Array<() => void> }; mtimes: Record<string, string>; editing: boolean; mode: "raw" | "rendered"; close(): void };
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const mt = cur!.mtimes[p];
  return { status: mt === undefined ? 404 : 200, headers: { get: (h: string) => (h === "X-Romp-Mtime-Ns" && mt !== undefined ? mt : null) } };
};
function rows(code: El, src: string): void {
  const lines = src.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  code.replaceChildren(...lines.map((ln) => {
    const cl = new El("span"); cl.className = "fv-cl";
    const ct = new El("span"); ct.className = "fv-ct";
    if (ln) ct.appendChild(new Txt(ln));
    cl.appendChild(ct);
    return cl;
  }));
}
function world(): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  const actions = new El("div"); actions.className = "fileview-actions"; actions.appendChild(new Txt("Rendered · Raw"));   // a node OUTSIDE the body
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre);
  body.appendChild(wrap);
  main.appendChild(actions); main.appendChild(body);
  rows(code, DOC);
  const w = { posted: [] as any[], main, body, code, actions, hooks: { rendered: [] as Array<() => void>, selection: [] as Array<(s: Selection) => void>, close: [] as Array<() => void> }, mtimes: {} as Record<string, string>, editing: false, mode: "raw" } as World;
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => w.mode, text: () => DOC, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: (cb) => { w.hooks.selection.push(cb); },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: () => { /* inert */ }, scrollToOffset: () => { /* inert */ },
    reload: () => { rows(code, DOC); for (const cb of w.hooks.rendered) cb(); },
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
const lastOf = (w: World, type: string, verb?: string) => [...w.posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status")): void {
  assert.ok(m, "a status ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
async function openPanel(w: World): Promise<void> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, status()); await flush();
  button.click();
  answer(w, status()); await flush(); await flush();
  assert.ok(w.main.querySelector(".fileview-aside"), "the panel is mounted beside the body");
}
function textNodeWith(root: El, needle: string): { node: Txt; at: number } {
  const hit = (function find(n: El): { node: Txt; at: number } | null {
    for (const c of n.childNodes) {
      if (c instanceof Txt) { const i = c.data.indexOf(needle); if (i >= 0) return { node: c, at: i }; }
      else { const r = find(c); if (r) return r; }
    }
    return null;
  })(root);
  assert.ok(hit, "the passage " + JSON.stringify(needle) + " is in the DOM");
  return hit!;
}
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const RECT_A: Rect = { left: 100, top: 200, right: 300, bottom: 220, width: 200, height: 20 };
const RECT_B: Rect = { left: 100, top: 200, right: 240, bottom: 220, width: 140, height: 20 };
const RECT_MOVED: Rect = { left: 100, top: 40, right: 300, bottom: 60, width: 200, height: 20 };
/** A selection as the panel reads it: the passage's text node from `at` for `length` characters, its rect `rect` (a fake
 *  selection's; the stand-in lays nothing out). */
function selectionOn(root: El, passage: string, length: number, rect: Rect): any {
  const hit = textNodeWith(root, passage);
  const sel = { rangeCount: 1, isCollapsed: false, anchorNode: hit.node, anchorOffset: hit.at, focusNode: hit.node, focusOffset: hit.at + length,
    toString: () => passage.slice(0, length), getRangeAt: () => ({ getBoundingClientRect: () => sel.rect }), rect };
  return sel;
}
const theFloat = (): El => { const all = doc.body.querySelectorAll(".fc-float"); return all[all.length - 1]; };
/** Where showFloat puts the button for a rect (its own arithmetic: beside the selection's end, above its line, kept on screen). */
const placeOf = (r: Rect) => ({ left: Math.min(Math.max(8, r.right + 6), win.innerWidth - 90) + "px", top: Math.min(Math.max(8, r.top - 30), win.innerHeight - 34) + "px" });
const shown = (f: El) => ({ hidden: f.hidden, left: f.style.left, top: f.style.top });
/** A drag's end as the seam reports it: the hook runs with the selection, and the float is offered beside it. */
function dragOffer(w: World, sel: any): El {
  selection = sel;
  for (const cb of w.hooks.selection) cb(sel);
  const f = theFloat();
  assert.equal(f.hidden, false, "the seam's mouseup offers the float");
  return f;
}
/** The panel open, a drag's offer standing on the whole passage. */
async function offered(t: TestContext): Promise<{ w: World; float: El; sel: any }> {
  const w = world(); t.after(() => w.close());
  t.after(() => { selection = null; });
  await openPanel(w);
  const sel = selectionOn(w.body, QUOTE, QUOTE.length, RECT_A);
  const float = dragOffer(w, sel);
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) });
  return { w, float, sel };
}

test("a selectionchange with the selection the float is already offered beside changes nothing: shown, it stays where it is; hidden by a scroll that moved the passage, it stays hidden (the seam's re-seat of the same selection is no new offer)", async (t) => {
  const { w, float, sel } = await offered(t);
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) }, "the same selection: the float stands where the drag put it");
  // the body scrolls and the passage moves from under the button: the float goes (hideFloatOnScroll)
  sel.rect = RECT_MOVED;
  dispatch(w.body, new Ev("scroll"));
  assert.equal(float.hidden, true, "hidden by the scroll");
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "the same selection again (a re-seat after a paint fires this too): no second offer");
});

test("a DIFFERENT non-collapsed selection inside the body shows the float at the new rect: the selection shrunk by Shift+Arrow after a drag moves the button with it (before, it stayed where the drag left it)", async (t) => {
  const { w, float } = await offered(t);
  selection = selectionOn(w.body, QUOTE, 9, RECT_B);   // the drag's selection with three words fewer at its end, a narrower rect
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "offered beside the shrunk selection");
  // ...and hidden by a scroll, a further change offers it again
  selection.rect = RECT_MOVED; dispatch(w.body, new Ev("scroll"));
  assert.equal(float.hidden, true);
  selection = selectionOn(w.body, QUOTE, 5, RECT_B);
  documentEvent("selectionchange");
  assert.equal(float.hidden, false, "a new selection after the scroll: offered again");
});

test("a collapsed selection hides the float (the keyboard collapsed it); a picture's offer, which answers to no selection, stands", async (t) => {
  const { w, float } = await offered(t);
  const words = textNodeWith(w.body, QUOTE).node;
  selection = { rangeCount: 1, isCollapsed: true, anchorNode: words, anchorOffset: 3, focusNode: words, focusOffset: 3, toString: () => "", getRangeAt: () => ({ getBoundingClientRect: () => RECT_A }) };
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "collapsed: the passage the button was offered for is no longer selected");
  // a picture's float (onImageClick: a click on a rendered picture, the Rendered view's root holding it): the button is about the
  // picture, and the document's selection, collapsed by the click, says nothing about it
  const md = new El("div"); md.className = "fileview-md";
  const para = new El("p"); const img = new El("img"); img.rect = RECT_A; img.setAttribute("src", "figs/p95.png");
  para.appendChild(img); md.appendChild(para); w.body.appendChild(md);
  w.mode = "rendered";
  dispatch(img, new Ev("click"));
  assert.equal(float.hidden, false, "the click on the picture offers Comment on its embed line");
  documentEvent("selectionchange");
  assert.equal(float.hidden, false, "the collapsed selection leaves a picture's offer standing");
});

test("a selectionchange while a pointer is down does nothing (a drag keeps its one offer at mouseup and the float does not flicker mid-drag); the press over, the next change offers", async (t) => {
  const { w, float } = await offered(t);
  dispatch(w.body, new Ev("mousedown"));   // the document's capture listeners: hideFloatOnDown hides the float, the press flag goes up
  assert.equal(float.hidden, true, "a press anywhere else hides the float (hideFloatOnDown)");
  selection = selectionOn(w.body, QUOTE, 9, RECT_B);
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "mid-press: the selection's every change is the drag's, and offers nothing");
  dispatch(w.body, new Ev("mouseup"));
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the press over: the change offers the float beside the selection");
  // a touch press the same way
  dispatch(w.body, new Ev("touchstart"));
  selection = selectionOn(w.body, QUOTE, 5, RECT_B);
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "mid-touch: nothing");
  dispatch(w.body, new Ev("touchend"));
  documentEvent("selectionchange");
  assert.equal(float.hidden, false, "the finger lifted: offered");
});

test("a selection with an end outside the body (Ctrl+A puts one at the page's start; a selection in the aside) hides a passage's float and offers nothing", async (t) => {
  const { w, float } = await offered(t);
  const outside = w.actions.childNodes[0] as Txt;
  assert.ok(!w.body.contains(outside), "the title bar's text stands outside the body");
  selection = { rangeCount: 1, isCollapsed: false, anchorNode: outside, anchorOffset: 0, focusNode: textNodeWith(w.body, "More text").node, focusOffset: 4, toString: () => "the whole page", getRangeAt: () => ({ getBoundingClientRect: () => RECT_A }) };
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "the passage is no longer the selection: the float goes, and no offer is made for the page");
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "and stays hidden");
});

test("the passage-gone hide drops the record of the offer: the selection Shift+ArrowDown carried into the aside hides the float, and the selection Shift+ArrowUp brings back to exactly the ends the float was offered at offers again (before: the record stood past the hide, the returned selection read as the one already answered, and a live keyboard selection in the body had no button); the collapsed face the same; the scroll's hide keeps its record", async (t) => {
  const { w, float, sel } = await offered(t);
  const words = textNodeWith(w.body, QUOTE).node;
  // the aside the open panel mounted stands outside the body: Shift+ArrowDown past the body's last line lands the focus in it
  const aside = w.main.querySelector(".fileview-aside")!;
  const inAside = aside.querySelector("button")!;
  assert.ok(inAside && !w.body.contains(inAside), "the aside's button stands outside the body");
  selection = { rangeCount: 1, isCollapsed: false, anchorNode: sel.anchorNode, anchorOffset: sel.anchorOffset, focusNode: inAside, focusOffset: 0, toString: () => QUOTE + ".\n\nMore text here.\nComments", getRangeAt: () => ({ getBoundingClientRect: () => RECT_A }) };
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "the focus in the aside: the passage is no longer the selection, and the float goes");
  // Shift+ArrowUp: the selection back at the ends of the drag's offer, the same nodes and offsets and the same text, and a selectionchange for the move
  selection = selectionOn(w.body, QUOTE, QUOTE.length, RECT_A);
  assert.deepEqual([selection.anchorNode, selection.anchorOffset, selection.focusNode, selection.focusOffset, selection.toString()], [sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset, sel.toString()], "the returned selection has exactly the offer's ends and text");
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) }, "back at the offered ends: a live selection in the body, offered again (before: hidden, read as the selection already answered)");
  // the collapsed face: the keyboard collapses the selection (the float goes), and the selection back at the offered ends offers
  selection = { rangeCount: 1, isCollapsed: true, anchorNode: words, anchorOffset: 3, focusNode: words, focusOffset: 3, toString: () => "", getRangeAt: () => ({ getBoundingClientRect: () => RECT_A }) };
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "collapsed: the float goes");
  selection = selectionOn(w.body, QUOTE, QUOTE.length, RECT_A);
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) }, "back at the offered ends after the collapse: offered again");
  // the scroll's hide keeps its record, as before: the same selection re-seated after it makes no second offer
  selection.rect = RECT_MOVED; dispatch(w.body, new Ev("scroll"));
  assert.equal(float.hidden, true, "hidden by the scroll");
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "the same selection after the scroll's hide: no second offer (a scroll fires no selectionchange, and the re-seat of the same ends is none)");
});

test("while the editor holds the body its selections are edits: a selectionchange offers nothing", async (t) => {
  const { w, float } = await offered(t);
  dispatch(w.body, new Ev("mousedown")); dispatch(w.body, new Ev("mouseup"));   // the drag's offer hidden by a press, the press over
  assert.equal(float.hidden, true);
  w.editing = true;
  selection = selectionOn(w.body, QUOTE, 9, RECT_B);
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "editing: nothing");
  w.editing = false;
  documentEvent("selectionchange");
  assert.equal(float.hidden, false, "the read view back: the same change offers");
});

test("a right or middle press raises no press flag (Chromium on Linux and macOS opens the native context menu on the right mousedown and the menu takes the release, so no mouseup follows): the keyboard change after it offers the float (before: the flag stood until the next left click, and the keyboard offered nothing)", async (t) => {
  const { w, float } = await offered(t);
  dispatch(w.body, new Ev("mousedown", { button: 2 }));   // the right button: hideFloatOnDown hides the float, as for any press...
  assert.equal(float.hidden, true, "a press of any button hides the float (hideFloatOnDown)");
  // ...and no mouseup comes: the menu took it. The reader dismisses the menu and widens the selection from the keyboard
  selection = selectionOn(w.body, QUOTE, 9, RECT_B);
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the right press raised no flag: the keyboard's change offers the float beside the selection");
  // the middle button the same way (no click, no selection of its own)
  dispatch(w.body, new Ev("mousedown", { button: 1 }));
  assert.equal(float.hidden, true);
  selection = selectionOn(w.body, QUOTE, 5, RECT_B);
  documentEvent("selectionchange");
  assert.equal(float.hidden, false, "a middle press raised no flag either");
  // a primary press still holds the flag through its drag, and its mouseup ends it
  dispatch(w.body, new Ev("mousedown", { button: 0 }));
  selection = selectionOn(w.body, QUOTE, 7, RECT_B);
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "mid-press with the primary button: the drag's changes offer nothing");
  dispatch(w.body, new Ev("mouseup", { button: 0 }));
  documentEvent("selectionchange");
  assert.equal(float.hidden, false, "the primary press over: offered");
});

test("a primary press the browser ended itself is over at its contextmenu (ctrl+click on macOS, a long press on a touch screen: the menu takes the release and no mouseup follows), and at the window's blur (a release in another frame never reaches this one): the keyboard change after either offers", async (t) => {
  const { w, float } = await offered(t);
  dispatch(w.body, new Ev("mousedown", { button: 0 }));
  assert.equal(float.hidden, true);
  selection = selectionOn(w.body, QUOTE, 9, RECT_B);
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "the press stands: nothing offered");
  dispatch(w.body, new Ev("contextmenu", { button: 0 }));   // the browser's menu opened on this press; the mouseup goes to the menu
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the contextmenu ended the press: the keyboard's change offers (before: the flag stood until the next left click)");
  // the window's blur ends a press the same way
  dispatch(w.body, new Ev("mousedown", { button: 0 }));
  assert.equal(float.hidden, true);
  selection = selectionOn(w.body, QUOTE, 5, RECT_B);
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "the press stands");
  win.dispatchEvent(new Event("blur"));
  documentEvent("selectionchange");
  assert.equal(float.hidden, false, "the window's blur ended the press: offered");
  // a touch press has no button and is held as before, to its touchend
  dispatch(w.body, new Ev("touchstart"));
  selection = selectionOn(w.body, QUOTE, 7, RECT_B);
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "mid-touch: nothing");
  dispatch(w.body, new Ev("touchend"));
  documentEvent("selectionchange");
  assert.equal(float.hidden, false, "the finger lifted: offered");
});

test("the document's listeners leave at dispose: selectionchange, and the press flag's mousedown, touchstart, mouseup, touchend, touchcancel, dragend and contextmenu, and the window's blur", async (t) => {
  const count = (type: string) => doc.listeners.filter((l) => l.type === type).length;
  const winCount = (type: string) => winListeners.filter((l) => l.type === type).length;
  const before = { sc: count("selectionchange"), md: count("mousedown"), ts: count("touchstart"), mu: count("mouseup"), te: count("touchend"), tc: count("touchcancel"), de: count("dragend"), cm: count("contextmenu"), bl: winCount("blur") };
  const w = world(); t.after(() => w.close());   // beside the explicit close below: a count that fails before it would leave the panel's poll timer holding the process, and the run would hang instead of reporting (dispose tolerates the second call)
  t.after(() => { selection = null; });
  await openPanel(w);
  const during = { sc: count("selectionchange"), md: count("mousedown"), ts: count("touchstart"), mu: count("mouseup"), te: count("touchend"), tc: count("touchcancel"), de: count("dragend"), cm: count("contextmenu"), bl: winCount("blur") };
  assert.deepEqual(during, { sc: before.sc + 1, md: before.md + 2, ts: before.ts + 2, mu: before.mu + 1, te: before.te + 1, tc: before.tc + 1, de: before.de + 1, cm: before.cm + 1, bl: before.bl + 1 }, "one selectionchange listener; the press flag beside hideFloatOnDown on mousedown and touchstart, and its six ends, the window's blur among them");
  w.close();
  const after = { sc: count("selectionchange"), md: count("mousedown"), ts: count("touchstart"), mu: count("mouseup"), te: count("touchend"), tc: count("touchcancel"), de: count("dragend"), cm: count("contextmenu"), bl: winCount("blur") };
  assert.deepEqual(after, before, "every one removed with the viewer");
});
