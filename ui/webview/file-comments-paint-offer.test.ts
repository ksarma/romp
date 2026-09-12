// The Comment float and the panel's OWN paints (plans/markdown-viewer.md Slice 5, item 9; file-comments.ts onSelectionChange,
// afterPaint, offeredFor; the Slice 5 review, round 1). Three defects of the slice's selectionchange listener, each with the case
// that failed before its fix:
// (1) A paint that is no gesture of the person's (a peer's comment landing through the poll, a settings pick from another pane)
//     unwraps and re-wraps the highlights, and a selection end inside a mark's text collapses to the mark's place, so a selection
//     overlapping a highlight is cut short and the browser fires selectionchange for the move. The listener compared the changed ends
//     with the OFFER's, read the change as a new selection of the person's, and re-offered a float a scroll had hidden, beside a
//     passage nobody selected. Now paintAll and repaintPresel end by reading the selection as they left it into the record the
//     listener compares with (afterPaint), so the paint's own event is no offer and the float stays as the paint found it, shown
//     or hidden; the person's next change offers.
// (2) offeredFor held the offer's two nodes and nothing cleared it, so after a reload replaced the body the whole previous render
//     stayed reachable behind it until the next offer (a WeakRef over the selected text node, collected only once the record is gone).
//     Now the record is read from the live selection after every paint, and holds no node of a swapped-out render.
// (3) The same-selection guard ran Selection.toString before the four end compares, and a changed selection stringified twice (the
//     guard's read and onSelection's). Now the ends come first and the text is read once, for ends that match or handed on.
// (4) The paint's writes can leave NOTHING selected with no selectionchange at all (the review's round 2): a highlight that is its
//     paragraph's whole text is the <p>'s only child, so the unwrap and the wrap again of its mark collapse a selection inside it to
//     the paragraph, and Chromium fires the event only where a text node is merged (the unpaint's normalize) or split (the wrap),
//     which a lone-child mark never is. The listener's collapsed-selection guard never ran, and a shown float stood beside nothing
//     until a click on it hid it and opened no composer. Now afterPaint hides a passage's float the writes left beside no selection
//     (the listener's own rule, passageGone); a float beside a selection cut short but standing stays, as (1) has it.
// (5) The writes can also cut the selection to a remnant with NO box (the review's round 5): a selection from inside a paragraph's
//     highlight into the next block's start keeps its focus there while the rewrap moves its anchor to the paragraph's end (a removed
//     node's descendant boundary points move to its parent), a bare line break between two blocks, in the body and not collapsed but
//     with no client rect. passageGone read it as a standing passage and the float stayed shown beside text nobody can see; the offer
//     itself refuses such a selection (onSelection's guard on a range with no width and no height), and a click on the button opened a
//     composer the whitespace refusal closed at once. Now afterPaint hides the float when the remnant has no box too, by the subject
//     test hideFloatOnScroll reads (floatSubjectRect); a remnant with a box keeps the float, as (4) has it.
// (6) The writes can cut the selection to a remnant WITH a box that has MOVED from under the button (the review's round 6): the same
//     drag carried into the next paragraph's middle leaves the line break and that paragraph's first half, a line or more below the
//     offer's box, and the float stayed where the offer put it, 74 px above the passage it now offered to comment on, while a scroll
//     that moves the passage one pixel hides it. Now afterPaint reads the scroll's whole test (subjectHeld: the remnant's top and
//     right edges within a pixel of the offer's): a remnant under the button keeps the float, one moved a pixel or more loses it.
// (7) The writes can move the selection WHOLE, not a character cut (the review's round 7): a peer's comment landing through the poll
//     on the selection's own line, before it, on it or inside it, wraps a mark whose 2 px side padding (.fc-hl) puts the still-selected
//     text 4 px further right, and (6)'s test read the displacement as the subject gone from under the button and hid the offer while
//     the passage stood selected and visible (8924fa17e and main kept it, 4 px off). Now afterPaint tells a selection moved whole from a
//     remnant by the seam's own test of a selection its paint left standing (the same text between two ends in the body, read against
//     the record as the last paint left it; not the ends by node identity, which the wrap's split of the text node renames) and offers
//     the float again beside the selection's box now, re-recording the place the scroll's test measures from; a remnant goes as (6) has it.
// (8) A float HIDDEN with its place record kept (the review's round 8): the picture overlay's press hid the float by its hidden bit alone
//     and left floatAt standing, which (7)'s re-seat read as a showing float, so a peer's mark landing through the poll on the
//     still-selected line while the person pressed on a picture, or after a click on a region's rectangle had opened its card, showed
//     the passage's Comment button again beside a selection the press had dismissed. Now the press goes through hideFloat (its record
//     cleared with it; file-comments-regions.test.ts pins the line) and afterPaint guards on the hidden bit, as hideFloatOnScroll does:
//     hidden, it stays hidden, whatever hid it.
// (9) A selection the writes moved WHOLE past the BODY'S BOX (the same round): the body clips what it scrolls and showFloat clamps to the
//     window alone, so a paint that pushed a last-visible-line selection below the body's bottom edge (Show changes inline toggled from
//     the keyboard, the struck label above the line growing the text) seated the button 30 px above a passage nobody can see, over the
//     body's last visible line and the other text it holds, and a click on it commented on text out of view. Now the re-seat takes a box
//     at least partly inside the body's (inBodyBox) and hides otherwise, as (6) has a remnant that moved; the stand-in's body wears a box
//     for that read (BODY_BOX), every offer's rect inside it.
// Driven over the behavior suite's DOM stand-in with the selection faked per case (window.getSelection is what the panel reads and
// what afterPaint records), the document's listeners run as the browser runs them, and the seam's paint fired through its hook.
// file-comments-paint-offer-browser.test.ts runs (1) over the real viewer in Chromium, where the paint moves the selection itself.
// Nodes hide their edges at construction (hideEdges, ui/test-dom-shim.ts). Synthetic fixtures only: the notes-api world,
// placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
import { hideEdges } from "../test-dom-shim";
import * as v8 from "node:v8";
import * as vm from "node:vm";

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
  detail = 0;
  constructor(public type: string, init: { key?: string } = {}) { this.key = init.key || ""; hideEdges(this); }
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
  const body = new El("div"); body.className = "fileview-body"; body.rect = BODY_BOX;   // the pane's clip, read by afterPaint's re-seat (9)
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
const RECT_NONE: Rect = { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };   // a range with no client rect: a bare line break between two blocks
const RECT_BELOW: Rect = { left: 100, top: 274, right: 245, bottom: 314, width: 145, height: 40 };   // a remnant a line or more below the offer's box: the next paragraph's first half (the review's 500 px measurement: top 74 px down, the right edge 55 px in)
const RECT_PADDED: Rect = { left: 100, top: 200, right: 304, bottom: 220, width: 204, height: 20 };   // the whole passage 4 px wider to the right: a peer's mark landed on it or inside it, and the mark's 2 px side padding stands inside the selection (the round-7 probes: dRight 4, dTop 0; a mark landing BEFORE the selection on its line moves both edges 4 px)
const RECT_LINE_DOWN: Rect = { left: 100, top: 220, right: 300, bottom: 240, width: 200, height: 20 };   // the whole passage one line down, its edges otherwise the offer's
const BODY_BOX: Rect = { left: 0, top: 100, right: 1000, bottom: 600, width: 1000, height: 500 };   // the body's box in the stand-in, the pane's clip (world): every offer's rect above sits inside it; afterPaint's re-seat reads it (the review's round 8)
const RECT_BELOW_CLIP: Rect = { left: 100, top: 601, right: 300, bottom: 621, width: 200, height: 20 };   // the whole passage moved just past the body's bottom edge, out of view (the round-8 probe at 500 px: a last-visible-line selection at 241.7 to 259.7 pushed to 264.1 to 282.1 under a body bottom of 262.75)
const RECT_ABOVE_CLIP: Rect = { left: 100, top: 70, right: 300, bottom: 90, width: 200, height: 20 };   // ...and past its top edge
const RECT_EDGE: Rect = { left: 100, top: 590, right: 300, bottom: 610, width: 200, height: 20 };   // the whole passage straddling the body's bottom edge: partly in view
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

/** A garbage collection on demand, without a command-line flag: the V8 flag set at run time and `gc` read from a fresh context. */
const gc: () => void = (() => { v8.setFlagsFromString("--expose-gc"); return vm.runInNewContext("gc"); })();
/** A turn's end (a WeakRef's target is held through the job that read it), then two full collections. */
const settle = async (): Promise<void> => { await new Promise<void>((r) => setImmediate(r)); gc(); await new Promise<void>((r) => setImmediate(r)); gc(); };
/** The seam's onRendered for a paint: the panel hides the float and runs paintAll over the body as it stands (the stand-in's rows are
 *  untouched; the selection the fake reports when the pass ends is what the paint "left", the stand-in laying nothing out). */
const paintHook = (w: World): void => { for (const cb of w.hooks.rendered) cb(); };
/** A settings pick from another pane (settings.ts onExternalSettingsChange: the same-document signal): the live panel repaints the
 *  marks with no gesture and no hideFloat, the poll's shape for a float that is showing. */
function externalFilterPick(): void {
  const ls = (globalThis as any).localStorage; const raw = ls.getItem("romp:settings");
  const cur = raw ? JSON.parse(raw) : {};
  ls.setItem("romp:settings", JSON.stringify({ ...cur, commentsFilter: cur.commentsFilter === "comments" ? "all" : "comments" }));
  win.dispatchEvent(new Event("romp:settings"));
}
/** The fake selection's toString counted: the panel's reads of the selected text. */
function countReads(s: any): () => number { let n = 0; const orig = s.toString; s.toString = () => { n++; return orig(); }; return () => n; }

/** A LIVE selection over the passage, as a browser's is: its nodes read at each access, so after a paint has unwrapped the
 *  passage's mark, normalized the row and wrapped it again (the text node replaced), the ends name the new node, as a live range's
 *  do; `length` is how far the selection reaches into the passage, cut short by the paint's collapse of an end (the fake is told). */
function liveSelectionOn(root: El, passage: string, length: number, rect: Rect): any {
  const hit = () => textNodeWith(root, passage);
  const sel = { rangeCount: 1, isCollapsed: false, length, rect,
    get anchorNode() { return hit().node; }, get anchorOffset() { return hit().at; }, get focusNode() { return hit().node; }, get focusOffset() { return hit().at + sel.length; },
    toString: () => passage.slice(0, sel.length), getRangeAt: () => ({ getBoundingClientRect: () => sel.rect }) };
  return sel;
}

test("the panel's own paint cuts an overlapping selection short and fires selectionchange: a float a scroll hid stays hidden (before: re-offered beside the truncated passage with no gesture), a float shown stays where it was offered, and the person's next change offers", async (t) => {
  const w = world(); t.after(() => w.close()); t.after(() => { selection = null; });
  await openPanel(w);
  const live = liveSelectionOn(w.body, QUOTE, QUOTE.length, RECT_A);
  const before = live.anchorNode;
  assert.ok(before.parentNode.classes.includes("fc-hl"), "the passage is highlighted: the selection's node is the mark's text");
  const float = dragOffer(w, live);
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) });
  live.rect = RECT_MOVED; dispatch(w.body, new Ev("scroll"));
  assert.equal(float.hidden, true, "hidden by a scroll that moved the passage");
  // the paint (the seam's hook: hideFloat, then paintAll) unwraps and re-wraps the highlight: the passage's text node is replaced,
  // and the selection's end inside the old node collapsed to the mark's place, so the selection reaches nine characters, not all
  live.length = 9; live.rect = RECT_B;
  paintHook(w);
  assert.notEqual(live.anchorNode, before, "the paint replaced the selection's node");
  assert.equal(String(live), QUOTE.slice(0, 9), "...and left the selection cut short");
  documentEvent("selectionchange");   // the event the paint's move fires, a task later
  assert.equal(float.hidden, true, "the paint's own selectionchange: no offer, the float stays hidden (before: shown beside the truncated selection, which nobody selected)");
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "the same selection again: still no offer");
  // the person's next change: offered beside it
  live.length = 5;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the keyboard's change after the paint offers the float");
  // a paint with no gesture while the float SHOWS (a settings pick from another pane: paintAll with no hideFloat, the poll's shape)
  // that cuts the selection again and leaves the remnant's box where the offer read it (the cut trims the selection inside the line
  // box the button sits beside: the fake's rect stays): the float stays as the paint found it, where main left it before the panel
  // heard selectionchange at all, and the paint's own event is no offer (a remnant the paint MOVES from under the button is (6)'s)
  live.length = 3;
  const mid = live.anchorNode;
  externalFilterPick();
  assert.notEqual(live.anchorNode, mid, "the pick's paint replaced the node again");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the remnant under the button: the pick itself hides nothing and moves nothing");
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the paint's own event moves nothing: the float stands where the person's selection put it");
  // ...and a person's change after that paint is an offer again, beside the selection's own rect
  live.length = 7; live.rect = RECT_A;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) }, "the next change offers beside the selection");
});

test("a paint that replaces the body releases the offer's nodes: the selected text node of the swapped-out render is collected once the reload has painted (before: held by the offer's record until the next selection), while an offer standing over its own render holds them", async (t) => {
  let { w, float, sel } = await offered(t);
  const text = new WeakRef<object>(sel.anchorNode); const row = new WeakRef<object>(sel.anchorNode.parentNode);
  assert.ok(w.body.contains(sel.anchorNode), "the offer's node stands in the body");
  // the browser's selection after the body's children are replaced: collapsed at the body (Chromium fires no selectionchange for it)
  selection = { rangeCount: 1, isCollapsed: true, anchorNode: w.body, anchorOffset: 0, focusNode: w.body, focusOffset: 0, toString: () => "", getRangeAt: () => ({ getBoundingClientRect: () => RECT_A }) };
  sel = null;   // the test holds nothing of the old render now: the panel's record is the one holder
  await settle();
  assert.ok(text.deref() !== undefined && row.deref() !== undefined, "the offer standing: the panel holds the selected node (the record the same-selection guard compares with)");
  // the reload replaces the rows (the seam's paint, `why` "paint"): the old render is swapped out
  w.ctx.reload();
  assert.equal(float.hidden, true, "onRendered hides the float");
  await settle();
  assert.equal(text.deref(), undefined, "the old render's text node is collected: nothing in the panel holds it (before: the offer's record did, until the next offer)");
  assert.equal(row.deref(), undefined, "...and its row with it");
  // the next selection on the new render offers as ever
  selection = selectionOn(w.body, QUOTE, QUOTE.length, RECT_A);
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) }, "a selection on the new render is offered");
});

test("the same-selection guard reads the selected text once, and only for ends that match: the offered selection re-fired costs one read; a changed selection costs one read too (before: two, the guard's and onSelection's) and is offered", async (t) => {
  const { w, float } = await offered(t);
  const same = selectionOn(w.body, QUOTE, QUOTE.length, RECT_A); const sameReads = countReads(same);
  selection = same;
  documentEvent("selectionchange");
  assert.equal(sameReads(), 1, "the ends match the offer's: the text is compared, one read");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) }, "the same selection: no new offer");
  const changed = selectionOn(w.body, QUOTE, 9, RECT_B); const changedReads = countReads(changed);
  selection = changed;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "a changed selection is offered beside its rect");
  assert.equal(changedReads(), 1, "...for one read of its text, the offer's own (before: the guard's read and then the offer's)");
  // a selection whose ends match the record but whose text differs (the guard's last compare): offered, one read shared with the offer
  const alike = selectionOn(w.body, QUOTE, 9, RECT_A); alike.toString = () => "other words"; const alikeReads = countReads(alike);
  selection = alike;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) }, "matching ends, other text: an offer");
  assert.equal(alikeReads(), 1, "the guard's one read is handed to the offer");
});

test("a paint whose writes collapse the selection to NOTHING, with no selectionchange (a highlight that is its paragraph's whole text: the mark is the <p>'s only child, and Chromium fires the event for a merged or split text node alone): the shown float goes with the paint itself (before: it stood beside nothing, and a click on it opened no composer); the next change offers; a selection cut short but standing keeps the float where it was; hidden, it stays hidden", async (t) => {
  const w = world(); t.after(() => w.close()); t.after(() => { selection = null; });
  await openPanel(w);
  const live = liveSelectionOn(w.body, QUOTE, QUOTE.length, RECT_A);
  const float = dragOffer(w, live);
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) });
  // a paint with no gesture while the float shows (a settings pick from another pane: paintAll with no hideFloat, the poll's shape)
  // collapses the selection to the paragraph, nothing selected, and no selectionchange follows: the fake is told, and none is fired
  live.isCollapsed = true; live.length = 0;
  externalFilterPick();
  assert.equal(String(live), "", "the paint left nothing selected");
  assert.equal(float.hidden, true, "the float went with the paint that left it beside no selection (before: shown, a Comment button that opened nothing)");
  // the person's next change offers again
  live.isCollapsed = false; live.length = 5; live.rect = RECT_B;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the keyboard's next selection offers the float");
  // a paint that cuts the selection short but not to nothing leaves a shown float where it was (case (1)'s rule stands)
  live.length = 3;
  externalFilterPick();
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "cut short, still a selection: the float stays where the offer put it");
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "...and the paint's own event moves nothing");
  // hidden by a scroll that moved the passage, a collapsing paint leaves it hidden
  live.rect = RECT_MOVED; dispatch(w.body, new Ev("scroll"));
  assert.equal(float.hidden, true, "hidden by the scroll");
  live.isCollapsed = true; live.length = 0;
  externalFilterPick();
  assert.equal(float.hidden, true, "hidden it stays");
  live.isCollapsed = false; live.length = 4; live.rect = RECT_B;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the next selection offers");
});

test("a paint whose writes cut the selection to a remnant with NO box (a selection from inside a paragraph's highlight into the next block's start: the rewrap moves its anchor to the paragraph's end, a bare line break between two blocks, in the body, not collapsed, no client rect): the shown float goes with the paint (before: it stood beside text nobody can see, and a click on it opened a composer the whitespace refusal closed); the next change offers; a remnant with a box keeps the float where it was; hidden, it stays hidden", async (t) => {
  const w = world(); t.after(() => w.close()); t.after(() => { selection = null; });
  await openPanel(w);
  const live = liveSelectionOn(w.body, QUOTE, QUOTE.length, RECT_A);
  let remnant: string | null = null;   // the text the fake reports once the paint has cut the selection to the break (null: the passage's own)
  live.toString = () => remnant ?? QUOTE.slice(0, live.length);
  const float = dragOffer(w, live);
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) });
  // a paint with no gesture while the float shows (a settings pick from another pane: paintAll with no hideFloat, the poll's shape)
  // leaves the selection a bare line break between the paragraph's end and the next block's start: the fake is told (not collapsed,
  // its nodes in the body, its rect empty), and no selectionchange follows
  live.length = 1; live.rect = RECT_NONE; remnant = "\n";
  externalFilterPick();
  assert.deepEqual([String(live), live.isCollapsed, w.body.contains(live.anchorNode)], ["\n", false, true], "the paint left a line break selected, not collapsed, in the body");
  const box = live.getRangeAt(0).getBoundingClientRect();
  assert.deepEqual([box.width, box.height], [0, 0], "...with no box");
  assert.equal(float.hidden, true, "the float went with the paint that left it beside a selection with no box, the offer's own refusal (before: shown, a Comment button that opened a composer the whitespace refusal closed at once)");
  // the person's next change offers again
  remnant = null; live.length = 5; live.rect = RECT_B;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the keyboard's next selection offers the float");
  // a paint that cuts the selection short to a remnant WITH a box leaves the shown float where it was (case (4)'s rule stands)
  live.length = 3;
  externalFilterPick();
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "cut short to a remnant with a box: the float stays where the offer put it");
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "...and the paint's own event moves nothing");
  // hidden by a scroll that moved the passage, a paint that leaves the boxless remnant leaves it hidden, and the next change offers
  live.rect = RECT_MOVED; dispatch(w.body, new Ev("scroll"));
  assert.equal(float.hidden, true, "hidden by the scroll");
  live.length = 1; live.rect = RECT_NONE; remnant = "\n";
  externalFilterPick();
  assert.equal(float.hidden, true, "hidden it stays");
  remnant = null; live.length = 4; live.rect = RECT_B;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the next selection offers");
});

test("a paint whose writes cut the selection to a remnant WITH a box that has MOVED from under the button (a drag from inside a whole-paragraph highlight into the next paragraph's middle: the rewrap moves the anchor to the paragraph's end, and the remnant, the line break and that paragraph's first half, sits a line or more below the offer's box): the shown float goes with the paint, by the test the scroll reads (before: it stood where the offer put it, 74 px above the passage it now offered to comment on); the paint's own event re-offers nothing; the next change offers; a remnant within a pixel keeps the float and one moved a pixel loses it; hidden, it stays hidden", async (t) => {
  const w = world(); t.after(() => w.close()); t.after(() => { selection = null; });
  await openPanel(w);
  const live = liveSelectionOn(w.body, QUOTE, QUOTE.length, RECT_A);
  const float = dragOffer(w, live);
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) });
  // a paint with no gesture while the float shows (a settings pick from another pane: paintAll with no hideFloat, the poll's shape)
  // cuts the selection and leaves the remnant's box a line below the offer's and shorter: the fake is told (in the body, not
  // collapsed, a box, moved), and the browser's selectionchange for the move, where it fires one, follows the paint
  live.length = 9; live.rect = RECT_BELOW;
  externalFilterPick();
  assert.deepEqual([String(live), live.isCollapsed, w.body.contains(live.anchorNode)], [QUOTE.slice(0, 9), false, true], "the paint left a remnant selected, in the body");
  const box = live.getRangeAt(0).getBoundingClientRect();
  assert.ok(box.width && box.height, "...with a box");
  assert.deepEqual([box.top - RECT_A.top, box.right - RECT_A.right], [74, -55], "...that moved from under the button by the review's measurement");
  assert.equal(float.hidden, true, "the float went with the paint that moved its subject from under it, as it goes on a scroll that moves the passage a pixel (before: shown where the offer put it, 74 px above the remnant, and a click on it commented on text the person had not chosen)");
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "the paint's own selectionchange is no offer: hidden it stays");
  // the person's next change offers, beside the selection as it stands
  live.length = 12;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_BELOW) }, "the keyboard's next selection offers the float beside the remnant");
  // a paint whose cut leaves the remnant within a pixel of the offer's box (the sub-pixel drift the scroll rule allows for) keeps it
  live.length = 10; live.rect = { ...RECT_BELOW, top: RECT_BELOW.top + 0.4, right: RECT_BELOW.right - 0.6 };
  externalFilterPick();
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_BELOW) }, "a remnant within a pixel of the offer's box keeps the float where the offer put it");
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_BELOW) }, "...and the paint's own event moves nothing");
  // ...and one whose right edge moved a pixel loses it, the scroll's threshold
  live.length = 11; live.rect = { ...RECT_BELOW, right: RECT_BELOW.right + 1 };
  externalFilterPick();
  assert.equal(float.hidden, true, "a remnant whose edge moved a pixel: the float goes, as on a scroll");
  // hidden by a scroll that moved the passage, a paint that moves the remnant leaves it hidden, and the next change offers
  live.length = 12; live.rect = RECT_BELOW;
  documentEvent("selectionchange");
  assert.equal(float.hidden, false, "offered again for the next change");
  live.rect = RECT_MOVED; dispatch(w.body, new Ev("scroll"));
  assert.equal(float.hidden, true, "hidden by the scroll");
  live.length = 9; live.rect = RECT_A;
  externalFilterPick();
  assert.equal(float.hidden, true, "hidden it stays");
  live.length = 4; live.rect = RECT_B;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the next selection offers");
});

test("a paint whose writes move the selection WHOLE, not a character cut (a peer's comment landing through the poll on the selection's own line, before it, on it or inside it: the mark's 2 px side padding puts the still-selected text 4 px further right, its node split and renamed, its text the same): the shown float follows the passage to its box now (before: hidden by the remnant's test, the passage standing selected and visible with no Comment offer); the paint's own event re-offers nothing; the scroll's test measures from the new place; a remnant the writes cut AND moved still goes; hidden, it stays hidden", async (t) => {
  const w = world(); t.after(() => w.close()); t.after(() => { selection = null; });
  await openPanel(w);
  const live = liveSelectionOn(w.body, QUOTE, QUOTE.length, RECT_A);
  const float = dragOffer(w, live);
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) });
  // a paint with no gesture while the float shows (a settings pick from another pane: paintAll with no hideFloat, the poll's shape)
  // wraps a peer's mark on the selection's line: the selection's text node is replaced (the wrap's split), every selected character
  // stays selected, and the box stands 4 px further right, the mark's padding; the fake is told, and the browser's selectionchange for
  // the split follows the paint
  const before = live.anchorNode;
  live.rect = RECT_PADDED;
  externalFilterPick();
  assert.notEqual(live.anchorNode, before, "the paint replaced the selection's node");
  assert.equal(String(live), QUOTE, "...and left every selected character selected: no remnant, the passage moved whole");
  assert.deepEqual([live.rect.top - RECT_A.top, live.rect.right - RECT_A.right], [0, 4], "...4 px right of where the button was offered, the mark's padding");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_PADDED) }, "the float follows the passage the writes moved whole, offered again beside its box now (before: hidden by the subject test, the passage still selected and visible)");
  documentEvent("selectionchange");   // the event the split fires, a task later
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_PADDED) }, "the paint's own selectionchange re-offers nothing: the float stands where the paint seated it");
  // the scroll's test measures from the new place: a scroll that leaves the passage there keeps the float (the offer's record is the
  // box the float was re-seated beside, not the drag's), one that moves the passage a pixel hides it
  dispatch(w.body, new Ev("scroll"));
  assert.equal(float.hidden, false, "a scroll that moved nothing on screen keeps the float: the offer's record is the passage's new box");
  live.rect = { ...RECT_PADDED, top: RECT_PADDED.top + 1 };
  dispatch(w.body, new Ev("scroll"));
  assert.equal(float.hidden, true, "...and one that moves the passage a pixel hides it, as ever");
  // the person's next change offers, and a paint that moves the selection whole by more than the padding (a line down) follows too
  live.length = 9; live.rect = RECT_A;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) }, "the keyboard's next change offers");
  live.rect = RECT_LINE_DOWN;
  externalFilterPick();
  assert.equal(String(live), QUOTE.slice(0, 9), "the paint left the selection whole again");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_LINE_DOWN) }, "moved whole by a line: the float follows to the selection's box now");
  // a remnant the writes cut AND moved still goes (case (6)'s rule): the text changed, so this is no whole move
  live.length = 5; live.rect = RECT_BELOW;
  externalFilterPick();
  assert.equal(String(live), QUOTE.slice(0, 5), "the paint cut the selection to a remnant");
  assert.equal(float.hidden, true, "...and moved it from under the button: the float goes, as on a scroll (the remnant's rule stands)");
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "the paint's own selectionchange is no offer: hidden it stays");
  // hidden by a scroll that moved the passage, a paint that moves the selection whole re-offers nothing, and the next change offers
  live.length = 7; live.rect = RECT_B;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the next selection offers");
  live.rect = RECT_MOVED; dispatch(w.body, new Ev("scroll"));
  assert.equal(float.hidden, true, "hidden by the scroll");
  live.rect = { ...RECT_MOVED, right: RECT_MOVED.right + 4 };
  externalFilterPick();
  assert.equal(String(live), QUOTE.slice(0, 7), "the paint moved the selection whole");
  assert.equal(float.hidden, true, "hidden it stays: a float the scroll hid is offered again by the person's next change alone");
  live.length = 4; live.rect = RECT_B;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the next selection offers");
});

test("a float HIDDEN with its place record kept (what the picture overlay's press did until this round: the hidden bit set, floatAt standing), and a paint whose writes move the still-selected passage whole: the float stays hidden (before: shown again beside the moved passage, a selection the press had dismissed, while the person drew a region or a rectangle's card stood open); the paint's own event re-offers nothing; a scroll leaves it hidden; the person's next change offers", async (t) => {
  const w = world(); t.after(() => w.close()); t.after(() => { selection = null; });
  await openPanel(w);
  const live = liveSelectionOn(w.body, QUOTE, QUOTE.length, RECT_A);
  const float = dragOffer(w, live);
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) });
  // the press's hide as the overlay made it until this round: the hidden bit alone, the offer's place record kept (the panel's own
  // hideFloat clears it, and the press goes through hideFloat now; this is the shape afterPaint must read as a hidden float all the same)
  float.hidden = true;
  // a paint with no gesture (a settings pick from another pane: paintAll with no hideFloat, the poll's shape) moves the still-selected
  // passage whole, the mark's padding: the fake is told, and the browser's selectionchange for the split follows the paint
  live.rect = RECT_PADDED;
  externalFilterPick();
  assert.equal(String(live), QUOTE, "the paint left the passage whole");
  assert.equal(float.hidden, true, "hidden it stays: afterPaint re-seats a SHOWING float alone (before: shown again beside the moved passage, the record read as a showing float)");
  assert.deepEqual([float.style.left, float.style.top], [placeOf(RECT_A).left, placeOf(RECT_A).top], "...and keeps the place it was hidden at, not showFloat's for the moved box");
  documentEvent("selectionchange");   // the event the split fires, a task later
  assert.equal(float.hidden, true, "the paint's own selectionchange is no offer: hidden it stays");
  // a scroll that moves the passage leaves a hidden float hidden (hideFloatOnScroll's own guard)
  live.rect = RECT_LINE_DOWN; dispatch(w.body, new Ev("scroll"));
  assert.equal(float.hidden, true, "a scroll leaves it hidden");
  // a second paint that moves the passage whole again: still no re-seat
  live.rect = { ...RECT_LINE_DOWN, right: RECT_LINE_DOWN.right + 4 };
  externalFilterPick();
  assert.equal(float.hidden, true, "a second whole move re-seats nothing");
  // the person's next change offers, beside the selection as it stands
  live.length = 9; live.rect = RECT_B;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the keyboard's next change offers the float");
});

test("a paint whose writes move the selection WHOLE past the BODY'S BOX (the Show changes inline toggle pressed from the keyboard: the struck label above a last-visible-line selection pushes it below the body's bottom edge, the text the same): the float goes with the paint (before: seated 30 px above a passage nobody can see, over the body's last visible line and the other text it holds, and a click on it commented on text out of view); the paint's own event re-offers nothing; the next change offers; the same past the body's top edge; a box straddling the edge, partly in view, re-seats; hidden, it stays hidden", async (t) => {
  const w = world(); t.after(() => w.close()); t.after(() => { selection = null; });
  await openPanel(w);
  const box = w.body.getBoundingClientRect();
  assert.deepEqual([box.top, box.bottom], [BODY_BOX.top, BODY_BOX.bottom], "the stand-in's body wears the pane's box");
  const live = liveSelectionOn(w.body, QUOTE, QUOTE.length, RECT_A);
  const float = dragOffer(w, live);
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) });
  assert.ok(RECT_A.top >= box.top && RECT_A.bottom <= box.bottom, "the offer's passage sits inside the body's box");
  // a paint with no gesture (a settings pick from another pane: paintAll with no hideFloat, the toggle's own shape, saveSettings then
  // paintAll) grows the text above the selected line and pushes the still-selected passage whole below the body's bottom edge: the
  // fake is told (in the body, not collapsed, the same text, a box out of the body's), and the browser's selectionchange, where the
  // paint fires one, follows
  live.rect = RECT_BELOW_CLIP;
  externalFilterPick();
  assert.equal(String(live), QUOTE, "the paint left the passage whole");
  assert.deepEqual([live.isCollapsed, w.body.contains(live.anchorNode)], [false, true], "...in the body, not collapsed");
  assert.ok(live.rect.top >= box.bottom, "...below the body's bottom edge, out of view");
  assert.equal(float.hidden, true, "the float goes with the paint: a passage moved out of the body's box is no re-seat (before: shown at top " + placeOf(RECT_BELOW_CLIP).top + ", 30 px above a passage nobody can see, over the body's last visible line)");
  documentEvent("selectionchange");
  assert.equal(float.hidden, true, "the paint's own selectionchange is no offer: hidden it stays");
  // the person's next change offers (the passage scrolled back into view, its box inside the body's)
  live.length = 9; live.rect = RECT_B;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the keyboard's next change offers the float");
  // past the body's top edge: the same, where the window clamp would have seated the button over the pane's header
  live.rect = RECT_ABOVE_CLIP;
  externalFilterPick();
  assert.ok(live.rect.bottom <= box.top, "the paint moved the passage above the body's top edge");
  assert.equal(float.hidden, true, "above the body's top edge: the float goes too");
  live.length = 12; live.rect = RECT_A;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_A) }, "the next change offers");
  // a whole move to a box straddling the bottom edge, partly in view: re-seated beside it, as (7) has a whole move
  live.rect = RECT_EDGE;
  externalFilterPick();
  assert.ok(RECT_EDGE.top < box.bottom && RECT_EDGE.bottom > box.bottom, "the box straddles the body's bottom edge");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_EDGE) }, "partly in view: the float follows the passage to its box now");
  // hidden by a scroll that moved the passage, a paint that moves it whole out of the box leaves it hidden, and the next change offers
  live.rect = RECT_MOVED; dispatch(w.body, new Ev("scroll"));
  assert.equal(float.hidden, true, "hidden by the scroll");
  live.rect = RECT_BELOW_CLIP;
  externalFilterPick();
  assert.equal(float.hidden, true, "hidden it stays");
  live.length = 4; live.rect = RECT_B;
  documentEvent("selectionchange");
  assert.deepEqual(shown(float), { hidden: false, ...placeOf(RECT_B) }, "the next selection offers");
});
