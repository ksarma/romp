// The margin layout's second review round (plans/file-review.md, "The margin-layout follow-on (2026-09-07)"), driven
// over the review stand-in (file-comments-margin-review.test.ts's: clamped scroll positions, a footer under the track,
// a body whose content reflows without its box changing): the centering of a card that fits the track (the card's top
// is TRACK content, which the lock scrolls with the body, so the scroll that shows the card's end has no header term —
// one added on top put an opened card's head under the panel's header), a pass without a render un-pushing a card
// (the leader's attribute and length leave the reused node), and the card a save landed in (a whole-file comment's card
// is loose at the top of the track, out of view for a reader anywhere but the top of the text: the save scrolled to it,
// until decision 43 made a save move nothing and put a line at the panel's foot saying where the card is, whose click
// scrolls to it). The numbers a real engine measures are file-comments-margin-fixes-browser.test.ts. The geometry here gives the
// track room for an open card (BODY_VIEW 260: a 160px track under a 120px open card), where the review stand-in's 100px
// track had none. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

// ── a DOM stand-in: ancestry, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; ctrlKey: boolean; metaKey: boolean;   // the save is Ctrl+Enter or Cmd+Enter since the composer follow-on (composerKeyAction)
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean } = {}) { this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; hideEdges(this); }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Reg = { type: string; cb: Listener; capture: boolean };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Txt {
  nodeType = 3;
  parentNode!: El | null;
  constructor(public data: string) {
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
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
// an attribute value may hold a quote or a backslash escaped with a backslash, as CSS.escape (or the panel's own
// fallback) writes it: `[data-id="x\"]"]` names the id `x"]`
const ATTR = /\[([\w-]+)(?:="((?:[^"\\]|\\.)*)")?\]/g;
const unescapeCss = (v: string): string => v.replace(/\\(.)/g, "$1");
function parseSel(sel: string): Compound[][] {
  return sel.split(",").map((g) => g.trim()).filter(Boolean).map((g) => g.split(/\s+/).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?((?:\.[\w-]+)*)((?:\[[\w-]+(?:="(?:[^"\\]|\\.)*")?\])*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    const classes = (m[2].match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
    const attrs: Array<[string, string | null]> = [];
    for (const a of m[3].matchAll(ATTR)) attrs.push([a[1], a[2] === undefined ? null : unescapeCss(a[2])]);
    return { tag: m[1] ? m[1].toUpperCase() : null, classes, attrs };
  }));
}
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const R = (left: number, top: number, width: number, height: number): Rect => ({ left, top, width, height, right: left + width, bottom: top + height });
const ZERO = R(0, 0, 0, 0);
/** An element's inline style as the layout writes it: plain properties, and the custom property through setProperty. */
class Style {
  [k: string]: unknown;
  setProperty(k: string, v: string): void { this[k] = v; }
  removeProperty(k: string): void { delete this[k]; }
  getPropertyValue(k: string): string { return typeof this[k] === "string" ? (this[k] as string) : ""; }
}
class El {
  nodeType = 1;
  tagName: string;
  parentNode!: El | null;
  childNodes!: Array<El | Txt>;
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; readOnly = false; title = ""; type = ""; value = ""; checked = false; placeholder = "";
  innerHTML = "";
  style = new Style();
  /** a picture's natural size and load state, a canvas's bitmap size (0×0: not drawn) */
  naturalWidth = 0; naturalHeight = 0; complete: boolean | undefined = undefined; width = 0; height = 0;
  /** the client rect a test gives the element outright (a picture, a page shell); the measurement table otherwise */
  rect: Rect | null = null;
  private st = 0;
  constructor(tag: string) {
    this.tagName = tag.toUpperCase();
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
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
  /** As the browser has it: a tabindex attribute, else 0 for a button or input, else -1 (not focusable). */
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : (this.tagName === "BUTTON" || this.tagName === "INPUT" ? 0 : -1); }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  dataset: Record<string, string> = new Proxy({} as Record<string, string>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))) as string,
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
    deleteProperty: (_, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes.slice()) this.detach(c); if (v !== "") this.appendChild(new Txt(v)); }
  /** A node leaves its parent; if it held the focus (itself or a descendant), the focus fixup rule moves it to the body. */
  private detach(n: El | Txt): void {
    const p = n.parentNode;
    if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; }
    if (n instanceof El && doc.activeElement && n.contains(doc.activeElement)) doc.activeElement = doc.body;
  }
  appendChild<T extends El | Txt>(n: T): T { if (n.parentNode) n.parentNode.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) n.parentNode.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes.slice()) this.detach(x); for (const x of c) this.appendChild(x); }
  remove(): void { if (this.parentNode) this.parentNode.detach(this); }
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
  /** Focus lands only on a focusable, enabled element — a div with no tabindex ignores focus(), as the browser does. */
  focus(): void { if (this.tabIndex >= 0 && !this.disabled) doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = doc.body; }
  scrollIntoView(): void { scrolledInto.push(this); }
  getBoundingClientRect(): Rect { return this.rect || (cur ? cur.measure(this) : ZERO); }
  get offsetWidth(): number { return 0; }
  /** The scroll position, clamped to the scroller's range as the browser clamps it: a write past the end lands at the
   *  end (and changes nothing when the scroller is already there), and a range that shrinks pulls the position back. */
  get scrollHeight(): number { return cur ? cur.scrollHeightOf(this) : 0; }
  get clientHeight(): number { return cur ? cur.clientHeightOf(this) : 0; }
  get scrollTop(): number { return Math.min(this.st, Math.max(0, this.scrollHeight - this.clientHeight)); }
  set scrollTop(v: number) { this.st = Math.max(0, Math.min(v, Math.max(0, this.scrollHeight - this.clientHeight))); }
  getContext(): { drawImage(): void } | null { return this.tagName === "CANVAS" ? { drawImage: () => { /* inert */ } } : null; }
  setPointerCapture(): void { /* inert */ }
  releasePointerCapture(): void { /* inert */ }
}
const scrolledInto: El[] = [];
const doc = {
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
};
doc.body = new El("body");
doc.activeElement = doc.body;
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
  if (ev.type === "load") { run(target instanceof El ? target.listeners : [], false, target as El); return true; }   // a load does not bubble: the target's own listeners alone
  for (const n of chain) if (run(n.listeners, false, n)) return !ev.defaultPrevented;
  run(doc.listeners, false, null);
  return !ev.defaultPrevented;
}
const win: any = new EventTarget();
win.parent = win; win.innerWidth = 1200; win.innerHeight = 800; win.devicePixelRatio = 1;
win.getSelection = () => null;
win.confirm = () => true;
(globalThis as any).window = win;
(globalThis as any).document = doc;
(globalThis as any).fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
// the layout's environment: the sheet's verdict on the fold, the frame queue, the observers
let narrow = false;
(globalThis as any).getComputedStyle = (el: El) => ({ flexDirection: el.classList.contains("fileview-main") && narrow ? "column" : "row" });
const frames: Array<() => void> = [];
(globalThis as any).requestAnimationFrame = (cb: () => void): number => { frames.push(cb); return frames.length; };
(globalThis as any).cancelAnimationFrame = (): void => { /* inert */ };
const flush = (): void => { for (const f of frames.splice(0)) f(); };
class RO {
  static all: RO[] = [];
  targets = new Set<El>();
  constructor(public cb: () => void) { RO.all.push(this); }
  observe(t: El): void { this.targets.add(t); }
  unobserve(t: El): void { this.targets.delete(t); }
  disconnect(): void { this.targets.clear(); }
}
(globalThis as any).ResizeObserver = RO;
/** Every observer holding `t` fires, then the frame runs: what a resize of that box does. */
const resized = (t: El): void => { for (const ro of RO.all) if (ro.targets.has(t)) ro.cb(); flush(); };
const resize = (): void => { for (const ro of RO.all) if (ro.targets.size) ro.cb(); };
const watched = (): Set<El> => { const s = new Set<El>(); for (const ro of RO.all) for (const t of ro.targets) s.add(t); return s; };
class IO {
  static all: IO[] = [];
  targets = new Set<El>();
  constructor(public cb: (entries: unknown[]) => void, public opts: unknown) { IO.all.push(this); }
  observe(t: El): void { this.targets.add(t); }
  unobserve(t: El): void { this.targets.delete(t); }
  disconnect(): void { this.targets.clear(); }
}
(globalThis as any).IntersectionObserver = IO;
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };
const tick = () => new Promise<void>((r) => setImmediate(r));

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const T0 = 1757145600000;
const QUOTE = "shipping the cache in v1.2";
// one logical line per row of the Raw view, each ROW px tall in the measurement table; blank rows between the later
// lines make each its own paragraph (the change groups are per paragraph), and the last row is the file's closing line
const LINES = ["# Report", "", "## Findings", "The api session cut p95 latency by 40% and the p99 by 10%.", "", "We recommend " + QUOTE + ".", "", "More text here."];
for (let i = 8; i < 33; i++) LINES.push(i % 2 ? "Line " + i + " of the report." : "");
LINES.push("The closing line of the report.");                    // row 33
const DOC = LINES.join("\n") + "\n";
const ROWS = LINES.length;                                       // 34
const passage: StoreComment = {   // row 5
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: QUOTE, prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const replied: StoreComment = {   // row 3
  id: (T0 - 60000) + "-40", author: "you", ts: T0 - 60000, body: "Cut this paragraph; it repeats the summary.",
  anchor: { quote: "The api session cut p95 latency by 40%", prefix: "## Findings\n", suffix: " and the" }, replies: [], resolved: false,
};
const whole: StoreComment = { id: (T0 - 120000) + "-0", author: "you", ts: T0 - 120000, body: "Add a summary at the top.", replies: [], resolved: false };
const detached: StoreComment = {
  id: (T0 - 90000) + "-7", author: "you", ts: T0 - 90000, body: "This claim needs a source.",
  anchor: { quote: "a paragraph the file no longer has", prefix: "", suffix: "" }, replies: [], resolved: false,
};
const closing: StoreComment = {   // row 33, the last line
  id: (T0 + 5000) + "-9", author: "you", ts: T0 + 5000, body: "End on the recommendation, not on this.",
  anchor: { quote: "The closing line of the report", prefix: "", suffix: "." }, replies: [], resolved: false,
};
const hunk: Hunk = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: DOC.indexOf("More"), curTo: DOC.indexOf("More") + 4, baseFrom: DOC.indexOf("More"), baseTo: DOC.indexOf("More"), oldText: "", newText: "More", anchor: null };   // row 7
/** An insertion of the word "Line" at the start of row i's line (rows 9, 11, … are each their own paragraph). */
const lineHunk = (n: number, i: number): Hunk => { const at = DOC.indexOf("Line " + i + " "); return { id: "h" + n, author: "api", ts: T0 - 30000 + n, kind: "ins", curFrom: at, curTo: at + 4, baseFrom: at, baseTo: at, oldText: "", newText: "Line", anchor: null }; };
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, detached, replied, passage, closing] },
    hunks: [hunk], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}
// media: a standalone image and a two-page PDF, each with one region comment
const PNG = "/repo/notes-api/docs/figure.png";
const PDF = "/repo/notes-api/docs/deck.pdf";
const H1 = "1111111111111111111111111111111111111111111111111111111111111111";
const IMG_RECT = R(100, 200, 300, 200);
const PAGE_RECTS = [R(100, 200, 306, 396), R(100, 616, 306, 396)];
const REGION = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 };
const RID = T0 + "-0";
const imageComment: StoreComment = { id: RID, author: "you", ts: T0, body: "Crop the header.", replies: [], resolved: false, target: { kind: "image", region: REGION, hash: H1 } as StoreComment["target"] };
const pageComment: StoreComment = { id: RID, author: "you", ts: T0, body: "Crop the header.", replies: [], resolved: false, target: { kind: "pdf", page: 2, region: REGION, hash: H1 } as StoreComment["target"] };
function mediaStatus(file: string, comments: StoreComment[]): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2F" + file + ".json", trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: null,
    store: { v: 3, path: "docs/" + file, suggestions: [], comments }, hunks: [], log: [],
    unsent: { comments: comments.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
    fileHash: H1,
  };
}

// ── the viewer stand-in: the body row, the seam as closures, a measurement table ───────────────────
// Geometry: the body's box is at viewport y=100, BODY_VIEW tall; the header stands OFFSET tall above the track and the
// footer FOOTER tall below it, so the track's box is TRACK tall; row i's text sits at 100 + ROW·i − scrollTop, rows
// from `reflowAt` on shifted down by `reflowBy` (a block above them opened); a card is CARD tall, OPEN when expanded.
const ROW = 60, OFFSET = 60, FOOTER = 40, CARD = 40, OPEN = 120, TALL = 200, BODY_VIEW = 260, TRACK = BODY_VIEW - OFFSET - FOOTER;   // TRACK 160: an open card fits, a tall one does not
const CONTENT = ROW * ROWS;                                     // 2040: the Raw view's own height
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  editing: boolean; viewMtime: string;
  content: number;                                             // the body's content height, padding aside
  reflowAt: number; reflowBy: number;
  measure(el: El): Rect; scrollHeightOf(el: El): number; clientHeightOf(el: El): number;
  setText(src: string): void; repaint(): void; close(): void;
  aside(): El; track(): El; list(): El; send(): El; card(key: string): El | null; top(key: string): number | null;
  cardIds(): string[];
};
let cur: World | null = null;
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
/** The percentages a region rectangle is placed by, read off its style attribute, as a box inside its overlay's. */
function regionBox(r: El, over: Rect): Rect {
  const pct: Record<string, number> = {};
  for (const m of (r.getAttribute("style") || "").matchAll(/(left|top|width|height):\s*([\d.]+)%/g)) pct[m[1]] = parseFloat(m[2]) / 100;
  return R(over.left + over.width * (pct.left || 0), over.top + over.height * (pct.top || 0), over.width * (pct.width || 0), over.height * (pct.height || 0));
}
function baseWorld(body: El, content: number): World {
  const main = new El("div"); main.className = "fileview-main";
  main.appendChild(body);
  doc.body.replaceChildren(main);
  const w = {
    posted: [] as any[], main, body, hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> }, editing: false,
    viewMtime: "1757145600000000001", content, reflowAt: ROWS, reflowBy: 0,
  } as World;
  const pad = (): number => parseFloat((body.style.paddingBottom as string) || "0") || 0;
  w.scrollHeightOf = (el) => {
    if (el === body) return Math.max(w.content + w.reflowBy + pad(), BODY_VIEW);
    if (el.classList.contains("fc-sec-cards")) { const l = el.childNodes.find((n) => n instanceof El) as El | undefined; return Math.max(l ? parseFloat((l.style.height as string) || "0") || 0 : 0, TRACK); }
    return 0;
  };
  w.clientHeightOf = (el) => (el === body ? BODY_VIEW : el.classList.contains("fc-sec-cards") ? TRACK : 0);
  w.measure = (el: El): Rect => {
    if (el === body) return R(0, 100, 400, BODY_VIEW);
    if (el.classList.contains("fc-sec-cards")) return R(400, 100 + OFFSET, 340, TRACK);
    if (el.classList.contains("fc-card")) return R(412, 0, 316, el.classList.contains("fc-tall") ? TALL : el.classList.contains("open") ? OPEN : CARD);   // fc-tall: a test's card taller than the track
    if (el.classList.contains("fc-hl") || el.classList.contains("fc-ins") || el.classList.contains("fc-del")) {
      const row = el.closest(".fv-cl");
      const i = row ? w.code.querySelectorAll(".fv-cl").indexOf(row) : -1;
      return i < 0 ? ZERO : R(20, 100 + ROW * i - body.scrollTop + (i >= w.reflowAt ? w.reflowBy : 0), 50, 20);
    }
    if (el.classList.contains("fc-imgwrap")) { const img = el.childNodes.find((c) => c instanceof El && c.tagName === "IMG") as El | undefined; return img ? img.getBoundingClientRect() : ZERO; }
    if (el.classList.contains("fc-overlay")) return el.parentNode ? el.parentNode.getBoundingClientRect() : ZERO;   // inset 0 in its wrap or its page's shell
    if (el.classList.contains("fc-region")) return el.parentNode ? regionBox(el, el.parentNode.getBoundingClientRect()) : ZERO;
    if (el.parentNode && el.parentNode.classList.contains("fc-cards")) return R(412, 0, 316, 20);   // a loader, a row, a fold button
    return ZERO;
  };
  w.aside = () => main.querySelector(".fileview-aside")!;
  w.track = () => w.aside().querySelector(".fc-sec-cards")!;
  w.list = () => w.track().querySelector(".fc-cards")!;
  w.send = () => w.aside().querySelector(".fc-sec-send")!;
  w.card = (key) => w.aside().querySelectorAll(".fc-card").find((c) => c.dataset.id === key) || null;
  w.top = (key) => { const c = w.card(key); const t = c ? c.style.top : undefined; return typeof t === "string" ? parseFloat(t) : null; };
  w.cardIds = () => w.list().querySelectorAll(".fc-card").map((c) => c.dataset.id);
  w.repaint = () => { for (const cb of w.hooks.rendered) cb(); };
  w.close = () => { for (const cb of w.hooks.close.splice(0)) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const noop = () => { /* inert */ };
function ctxBase(w: World, over: Partial<FileViewActionCtx>): FileViewActionCtx {
  return {
    path: ABS, sid: SID, todoId: null,
    body: () => w.body as unknown as HTMLElement, mode: () => "raw", text: () => DOC, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: noop, onSaved: noop, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => w.editing, setTrackedEdit: (_t: TrackedEdit | null) => { /* inert */ }, guardClose: noop,   // the viewer's close ask (main, 2026-09-07): the stand-in asks nothing
    aside: (node) => { w.main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); w.main.appendChild(n); } },
    setMode: noop, scrollToOffset: noop, reload: noop,
    ...over,
  };
}
/** The Raw view of `src` (DOC unless given): `.fileview-code > pre > code.hljs` with a row per line. */
function textWorld(src = DOC): World {
  const body = new El("div"); body.className = "fileview-body";
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre); body.appendChild(wrap);
  const w = baseWorld(body, ROW * (src.split("\n").length - 1));
  w.code = code;
  let text = src;
  rows(code, text);
  w.setText = (s) => { text = s; rows(code, s); w.repaint(); };
  w.ctx = ctxBase(w, { text: () => text });
  return w;
}
/** A standalone image: `.fileview-imgbox > img.fileview-img`, the picture's box given outright. */
function imageWorld(): World & { img: El } {
  const body = new El("div"); body.className = "fileview-body";
  const box = new El("div"); box.className = "fileview-imgbox";
  const img = new El("img"); img.className = "fileview-img"; img.setAttribute("src", "blob:romp/figure");
  img.rect = IMG_RECT; img.naturalWidth = 600; img.naturalHeight = 400; img.complete = true;
  box.appendChild(img); body.appendChild(box);
  const w = baseWorld(body, 400) as World & { img: El };
  w.img = img; w.code = new El("code");
  w.setText = noop;
  w.ctx = ctxBase(w, { path: PNG, mode: () => "media", text: () => null, media: () => "image", mediaElement: () => img as unknown as HTMLElement });
  return w;
}
/** A PDF's pages as the chunk builds them: `.fileview-pdfhost > .fileview-pdf > .fileview-pdf-page[data-page] >
 *  canvas.fileview-pdf-canvas`, each shell's box given outright (ZERO: a page with no box yet), no canvas drawn. */
function pdfWorld(rects: Array<Rect | null>): World & { pages: El[]; canvases: El[] } {
  const body = new El("div"); body.className = "fileview-body";
  const host = new El("div"); host.className = "fileview-pdfhost";
  const pdf = new El("div"); pdf.className = "fileview-pdf";
  const pages: El[] = [], canvases: El[] = [];
  rects.forEach((rect, i) => {
    const sh = new El("div"); sh.className = "fileview-pdf-page"; sh.dataset.page = String(i + 1); sh.rect = rect || ZERO;
    const c = new El("canvas"); c.className = "fileview-pdf-canvas"; c.dataset.page = String(i + 1); c.rect = rect || ZERO;
    sh.appendChild(c); pdf.appendChild(sh); pages.push(sh); canvases.push(c);
  });
  host.appendChild(pdf); body.appendChild(host);
  const w = baseWorld(body, 1040) as World & { pages: El[]; canvases: El[] };
  w.pages = pages; w.canvases = canvases; w.code = new El("code");
  w.setText = noop;
  w.ctx = ctxBase(w, { path: PDF, mode: () => "media", text: () => null, media: () => "pdf", mediaElement: () => pdf as unknown as HTMLElement, pdfPages: () => pages as unknown as HTMLElement[] });
  return w;
}
type Posted = Record<string, any>;
type Ctx = { after(fn: () => void): void };
async function open<W extends World>(t: Ctx, w: W, s: Status = status()) {
  t.after(() => w.close());                            // a failing assertion must not leave the panel alive (its deadline timers would hold the process)
  narrow = false; frames.length = 0; RO.all.length = 0; IO.all.length = 0; scrolledInto.length = 0; doc.activeElement = doc.body;
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  const last = (): Posted => w.posted[w.posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  const ok = (o: Status = s) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...o });
  await ok();                                          // the probe's status
  button.click();                                      // open: the aside mounts, the panel re-asks
  await ok();
  return { w, fc, button, ok, last };
}
// the desired top of a mark on row i in the track's content: the row's top in the body's content, less the header's height
const desired = (i: number): number => ROW * i - OFFSET;
const actIn = (root: El, a: string): El | null => root.querySelectorAll("[data-act]").find((x) => x.dataset.act === a) || null;
const headOf = (w: World, key: string): El => w.card(key)!.querySelector(".fc-card-head")!;
/** The viewport box a card's placed top gives it: the track's top, plus its top in the track's content, less the track's scroll. */
const cardBox = (w: World, key: string): { top: number; bottom: number } => { const top = 100 + OFFSET + w.top(key)! - w.track().scrollTop; return { top, bottom: top + w.card(key)!.getBoundingClientRect().height }; };
const TRACK_BOX = { top: 100 + OFFSET, bottom: 100 + OFFSET + TRACK };
const BODY_BOX = { top: 100, bottom: 100 + BODY_VIEW };
/** The viewport box of a comment's highlight, as the stand-in measures it. */
const markRect = (w: World, key: string): Rect => w.body.querySelectorAll(".fc-hl").find((m) => m.dataset.id === key)!.getBoundingClientRect();
const savedLineOf = (w: World): El | null => actIn(w.aside(), "fcsavedgo");   // the line at the foot for a saved card out of view (decision 43)
const inBox = (box: { top: number; bottom: number }, of: { top: number; bottom: number }): boolean => box.top >= of.top && box.bottom <= of.bottom;

// ── centering a card that fits the track ──────────────────────────────────────────────────────────

test("an opened card that fits the track is shown whole: the body scrolls the least that shows the card's end, and the card's head stays in the track's box — the head click, and the reference link on the open card", async (t) => {
  const { w } = await open(t, textWorld());
  const body = w.body, track = w.track();
  assert.ok(OPEN + 8 <= TRACK, "the fixture: an open card and the gap fit the track");
  headOf(w, replied.id).click(); await tick();          // row 3's card opens, OPEN tall, and the click centers it
  const card = w.card(replied.id)!;
  assert.ok(card.classList.contains("open"));
  assert.equal(w.top(replied.id), desired(3), "the card keeps its mark's height");
  // the mark's center would put the body at markY - view/2; the card's end (its top plus OPEN plus the gap, in the TRACK's
  // content, which scrolls with the body) needs more than that here, so the least scroll that shows the end wins — with
  // no header term: the header's height is already in the card's top (desired = the mark's top less the header)
  const markY = desired(3) + OFFSET;
  const center = markY - BODY_VIEW / 2;
  const showCard = desired(3) + OPEN + 8 - TRACK;
  assert.ok(showCard > center, "the fixture: the card's end needs more scroll than the mark's center: " + showCard + " vs " + center);
  assert.equal(body.scrollTop, showCard, "the least scroll that shows the card's end");
  assert.equal(track.scrollTop, showCard, "the track came along at once");
  const box = cardBox(w, replied.id);
  assert.ok(inBox(box, TRACK_BOX), "the whole card, its head included, is in the track's box: " + JSON.stringify(box) + " in " + JSON.stringify(TRACK_BOX));
  const mark = markRect(w, replied.id);
  assert.equal(box.top, mark.top, "and level with its mark");
  assert.ok(inBox(mark, BODY_BOX), "the mark is in the body's box: " + JSON.stringify(mark));
  // the header's height too far (the defect) would have put the head that far above the track's box
  assert.ok(box.top - TRACK_BOX.top < OFFSET, "sanity: a header-term scroll would have clipped the head by " + (OFFSET - (box.top - TRACK_BOX.top)) + "px");
  // the reference link on the open card, from elsewhere in the text: the same place
  body.scrollTop = 0; body.dispatchEvent(new Ev("scroll"));
  assert.equal(track.scrollTop, 0);
  actIn(card, "fcgoto")!.click();
  assert.equal(body.scrollTop, showCard, "the reference link lands the same scroll");
  assert.equal(track.scrollTop, showCard);
  assert.ok(inBox(cardBox(w, replied.id), TRACK_BOX), "the whole card is in the track's box again");
  // a card whose mark's center already shows its end: the center wins, and the card is in the box
  headOf(w, replied.id).click(); await tick();          // fold: nothing moves
  assert.equal(body.scrollTop, showCard);
  body.scrollTop = 0; body.dispatchEvent(new Ev("scroll"));
  actIn(w.card(passage.id)!, "fcgoto")!.click();       // row 5's closed card: CARD tall
  const markY5 = desired(5) + OFFSET;
  assert.ok(desired(5) + CARD + 8 - TRACK < markY5 - BODY_VIEW / 2, "the fixture: the center shows a closed card's end");
  assert.equal(body.scrollTop, markY5 - BODY_VIEW / 2, "the mark at the body's center");
  assert.ok(inBox(cardBox(w, passage.id), TRACK_BOX));
  w.close();
});

test("a card taller than the track: brought in as far as its end, the clipping at its head the excess over the track's box alone (or the header less the gap, where the mark's top would otherwise leave the body's box)", async (t) => {
  const { w } = await open(t, textWorld());
  const body = w.body, track = w.track();
  assert.ok(TALL + 8 > TRACK, "the fixture: a tall card does not fit the track");
  const card = w.card(replied.id)!;
  card.classList.add("fc-tall");                        // grown without a render (a long reply's turns): the card observer's pass
  resized(card);
  assert.equal(w.card(replied.id), card, "no render: the same node");
  assert.equal(w.top(passage.id), desired(3) + TALL + 8, "the card below moved down under it");
  actIn(card, "fcgoto")!.click();
  const excess = TALL + 8 - TRACK;
  const want = Math.min(desired(3) + TALL + 8 - TRACK, desired(3) + OFFSET - 8);
  assert.equal(body.scrollTop, want, "the least scroll that shows the card's end, capped where the mark's top would leave the box");
  assert.equal(track.scrollTop, want);
  const box = cardBox(w, replied.id);
  assert.ok(box.bottom <= TRACK_BOX.bottom, "the card's end is in the track's box: " + box.bottom + " vs " + TRACK_BOX.bottom);
  assert.equal(TRACK_BOX.top - box.top, Math.min(excess, OFFSET - 8), "clipped at the head by the excess alone: " + (TRACK_BOX.top - box.top));
  assert.ok(markRect(w, replied.id).top >= BODY_BOX.top, "the mark's top is in the body's box");
  w.close();
});

// ── a pass without a render un-pushes ─────────────────────────────────────────────────────────────

test("a pass without a render un-pushes a card the pass no longer pushes: the leader's attribute and its length leave the reused node — after a reflow that moved its mark down, and after the card above shrank", async (t) => {
  const { w } = await open(t, textWorld());
  headOf(w, replied.id).click(); await tick();          // row 3's card opens: its end (desired(3) + OPEN + 8 = 248) past row 5's mark (240)
  const node = w.card(passage.id)!;
  const pushedTo = desired(3) + OPEN + 8;
  assert.equal(w.top(passage.id), pushedTo, "pushed under the open card");
  assert.equal(node.dataset.pushed, "1");
  assert.equal(node.style.getPropertyValue("--fc-push"), (pushedTo - desired(5)) + "px", "the leader's length");
  // a reflow inside the body (a block between the two paragraphs opened): rows from 4 on sit 100px lower, the body's box
  // unchanged — the content observer's pass re-places the SAME nodes, no render
  const wrap = w.body.querySelector(".fileview-code")!;
  w.reflowAt = 4; w.reflowBy = 100;
  resized(wrap);
  assert.equal(w.card(passage.id), node, "the same node: no render");
  assert.equal(w.top(passage.id), desired(5) + 100, "level with its mark again");
  assert.equal(node.dataset.pushed, undefined, "no leader attribute on a level card (the sheet's [data-pushed]::before would draw one pointing at no passage)");
  assert.equal(node.style.getPropertyValue("--fc-push"), "", "and no leader length");
  // the reflow undone: pushed again, on the same node
  w.reflowAt = ROWS; w.reflowBy = 0;
  resized(wrap);
  assert.equal(w.card(passage.id), node);
  assert.equal(node.dataset.pushed, "1", "pushed again once the marks are back");
  assert.equal(node.style.getPropertyValue("--fc-push"), (pushedTo - desired(5)) + "px");
  // the card above shrinks without a render (a crop gone, a web font): the card observer's pass alone
  const above = w.card(replied.id)!;
  above.classList.remove("open");
  resized(above);
  assert.equal(w.card(passage.id), node, "still the same node");
  assert.equal(w.top(passage.id), desired(5), "level: the card above no longer reaches its mark");
  assert.equal(node.dataset.pushed, undefined);
  assert.equal(node.style.getPropertyValue("--fc-push"), "");
  w.close();
});

// ── a save scrolls to the card it landed in ───────────────────────────────────────────────────────

const NOTE = "Add a summary at the top, please.";
const fileComment = (id: string, body: string = NOTE): StoreComment => ({ id, author: "you", ts: parseInt(id, 10), body, replies: [], resolved: false });   // ts from the id's stamp: the loose group sorts by it
const NS9 = "1757145600000000009";
const withComments = (comments: StoreComment[], verb = "comment"): Status => status({ verb, storeMtimeNs: NS9, store: { v: 3, path: "docs/report.md", suggestions: [], comments } });
/** Comment on this file, a note typed, Enter: the `comment` request is out. */
async function saveFileComment(w: World, last: () => Posted): Promise<El> {
  actIn(w.aside(), "fcfile")!.click();
  const composer = w.aside().querySelector(".fc-composer")!;
  assert.equal(composer.hidden, false, "the composer is up");
  const input = composer.querySelector(".fc-input")!;
  input.value = NOTE;
  input.dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true }));   // the save chord (Enter alone adds a line)
  await tick();
  assert.equal(last().verb, "comment", "the comment went out");
  assert.equal(last().args.anchor, undefined, "a whole-file comment: no anchor");
  return composer;
}

test("a whole-file comment saved: the new card is loose at the top of the track, and the save moves nothing (decision 43; before: the least scroll that showed it, on both scrollers) — landing in view from the top of the text, no line; with the text scrolled down, the line at the foot says above and its click brings the card in on both scrollers; from the top with its end past the box, below, and the click shows its end", async (t) => {
  const { w, ok, last } = await open(t, textWorld());
  const body = w.body, track = w.track();
  // the text at its top: the card lands whole in the track's box, and nothing is said
  let composer = await saveFileComment(w, last);
  const fresh = fileComment(T0 + 5000 + "-0");
  await ok(withComments([whole, detached, replied, passage, closing, fresh]));
  assert.ok(w.card(fresh.id), "the new card is rendered");
  const top = 8 + 2 * (CARD + 8);                       // 104
  assert.equal(w.top(fresh.id), top, "loose: under the two loose cards at the top of the track, in the list's order");
  assert.ok(inBox(cardBox(w, fresh.id), TRACK_BOX), "the fixture: in view where it landed: " + JSON.stringify(cardBox(w, fresh.id)));
  assert.equal(body.scrollTop, 0, "nothing moved"); assert.equal(track.scrollTop, 0);
  assert.equal(composer.hidden, true, "the composer closed");
  assert.equal(savedLineOf(w), null, "a card in view needs no line");
  // well down the text: the new card is above the track's box
  body.scrollTop = 600; body.dispatchEvent(new Ev("scroll"));
  assert.equal(track.scrollTop, 600, "the reader is well down the text");
  composer = await saveFileComment(w, last);
  const second = fileComment(T0 + 5500 + "-0", "And a glossary at the end.");
  await ok(withComments([whole, detached, replied, passage, closing, fresh, second]));
  const secondTop = top + CARD + 8;                     // 152
  assert.equal(w.top(second.id), secondTop);
  assert.equal(body.scrollTop, 600, "the body stays (before: " + (secondTop - 8) + ", the least scroll that showed the card)");
  assert.equal(track.scrollTop, 600, "and the track");
  assert.deepEqual(scrolledInto, []);
  assert.equal(composer.hidden, true, "the composer closed");
  assert.equal(savedLineOf(w)!.textContent, "Saved · the card is above", "the line says where the card is");
  savedLineOf(w)!.click(); await tick();
  // the click: the least scroll that shows the card puts its top a gap under the box's top — on the BODY as well as the track,
  // at once (a track-only scroll reached the body only on the track's scroll event, which the browser folded into the
  // render's own write, so the body stayed and the next pass pulled the track back to it)
  assert.equal(body.scrollTop, secondTop - 8, "the body: the least scroll that shows the card (showLoose)");
  assert.equal(track.scrollTop, secondTop - 8, "the track with it, at once");
  assert.ok(inBox(cardBox(w, second.id), TRACK_BOX), "the card is in the track's box: " + JSON.stringify(cardBox(w, second.id)));
  assert.deepEqual(scrolledInto, [], "no scrollIntoView in the margin layout: the lock would not have carried it");
  assert.equal(savedLineOf(w), null, "the line is over");
  // the text at its top again: the fifth loose card's end is past the track's box
  body.scrollTop = 0; body.dispatchEvent(new Ev("scroll"));
  await saveFileComment(w, last);
  const third = fileComment(T0 + 5600 + "-0", "Number the figures.");
  await ok(withComments([whole, detached, replied, passage, closing, fresh, second, third]));
  const thirdTop = top + 2 * (CARD + 8);                // 200
  assert.equal(w.top(third.id), thirdTop);
  assert.ok(thirdTop + CARD + 8 > TRACK, "the fixture: from the top of the text, the fifth loose card's end is past the track's box");
  assert.equal(body.scrollTop, 0, "nothing moved (before: " + (thirdTop + CARD + 8 - TRACK) + ", the least scroll that showed the card's end)");
  assert.equal(savedLineOf(w)!.textContent, "Saved · the card is below");
  savedLineOf(w)!.click(); await tick();
  assert.equal(body.scrollTop, thirdTop + CARD + 8 - TRACK, "the click: the least scroll that shows the card's end");
  assert.equal(track.scrollTop, body.scrollTop);
  assert.ok(inBox(cardBox(w, third.id), TRACK_BOX), "the card is in the track's box: " + JSON.stringify(cardBox(w, third.id)));
  assert.deepEqual(scrolledInto, []);
  assert.equal(savedLineOf(w), null);
  w.close();
});

test("a reply saved on a card with the text scrolled away from it: nothing scrolls (decision 43; before: the card was centered as an opened card is), the card is the focus, level with its mark below the box, the composer closes, and the line says below — its click centers the card as an opened card is, the least scroll that shows its end", async (t) => {
  const { w, ok, last } = await open(t, textWorld());
  const body = w.body, track = w.track();
  headOf(w, passage.id).click(); await tick();          // the card opens (Reply stands in the open card) and the click centers it
  const showCard = desired(5) + OPEN + 8 - TRACK;
  assert.equal(body.scrollTop, showCard);
  actIn(w.card(passage.id)!, "fcreply")!.click(); await tick();
  const composer = w.aside().querySelector(".fc-composer")!;
  assert.equal(composer.hidden, false);
  body.scrollTop = 0; body.dispatchEvent(new Ev("scroll"));   // the reader looked at the top of the text meanwhile
  assert.equal(track.scrollTop, 0);
  const input = composer.querySelector(".fc-input")!;
  input.value = "Which cache do you mean?";
  input.dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true }));   // the save chord
  await tick();
  assert.equal(last().verb, "reply");
  assert.equal(last().args.commentId, passage.id);
  const replied5: StoreComment = { ...passage, replies: [{ author: "you", ts: T0 + 6000, body: "Which cache do you mean?" }] };
  await ok(withComments([whole, detached, replied, replied5, closing], "reply"));
  assert.ok(w.card(passage.id)!.classList.contains("open"), "the card stays open with its reply");
  assert.equal(body.scrollTop, 0, "the text stays at its top (before: " + showCard + ", the least scroll that shows the card's end)");
  assert.equal(track.scrollTop, 0);
  assert.ok(!inBox(cardBox(w, passage.id), TRACK_BOX), "the card is past the track's box: " + JSON.stringify(cardBox(w, passage.id)));
  assert.equal(cardBox(w, passage.id).top, markRect(w, passage.id).top, "level with its mark all the same: the focus");
  assert.deepEqual(scrolledInto, []);
  assert.equal(composer.hidden, true);
  assert.equal(savedLineOf(w)!.textContent, "Saved · the card is below");
  savedLineOf(w)!.click(); await tick();
  assert.equal(body.scrollTop, showCard, "the click brought the text to the card's mark: the least scroll that shows the card's end");
  assert.equal(track.scrollTop, showCard);
  assert.ok(inBox(cardBox(w, passage.id), TRACK_BOX), "the whole card is in the track's box");
  assert.equal(cardBox(w, passage.id).top, markRect(w, passage.id).top, "level with its mark");
  assert.deepEqual(scrolledInto, [], "a marked card is centered, not scrollIntoView'd");
  assert.equal(savedLineOf(w), null, "the line is over");
  w.close();
});

test("the saved comment is read off the reply's store: the one comment the status before the write did not hold; among several new ones (a retry after a moved fence), the one whose body is the note — the line's click goes to ours, not to the peer's; none identifiable, no line, and the composer closes all the same", async (t) => {
  const { w, ok, last } = await open(t, textWorld());
  const body = w.body;
  body.scrollTop = 600; body.dispatchEvent(new Ev("scroll"));
  // a peer's comment landed too (the reply after a retry holds both): ours by its body
  await saveFileComment(w, last);
  const mine = fileComment(T0 + 5000 + "-0"), peer = fileComment(T0 + 4000 + "-0", "Rename the section.");
  await ok(withComments([whole, detached, replied, passage, closing, peer, mine]));
  const mineTop = 8 + 3 * (CARD + 8), peerTop = 8 + 2 * (CARD + 8);   // the loose group by ts: whole, detached, the peer's, ours
  assert.equal(w.top(mine.id), mineTop); assert.equal(w.top(peer.id), peerTop);
  assert.equal(body.scrollTop, 600, "nothing scrolled (decision 43)");
  assert.equal(savedLineOf(w)!.textContent, "Saved · the card is above");
  savedLineOf(w)!.click(); await tick();
  assert.equal(body.scrollTop, mineTop - 8, "the click went to ours, not to the peer's (" + (peerTop - 8) + ")");
  assert.equal(w.track().scrollTop, mineTop - 8);
  body.scrollTop = 600; body.dispatchEvent(new Ev("scroll"));
  // two new comments with the note's body (nothing tells them apart): no line, and the save is not in doubt
  await saveFileComment(w, last);
  const twinA = fileComment(T0 + 7000 + "-0"), twinB = fileComment(T0 + 7001 + "-0");
  await ok(withComments([whole, detached, replied, passage, closing, peer, mine, twinA, twinB]));
  assert.equal(body.scrollTop, 600, "no card named: nothing scrolled, as ever");
  assert.equal(w.track().scrollTop, 600);
  assert.equal(savedLineOf(w), null, "no card named: no line");
  assert.deepEqual(scrolledInto, []);
  assert.equal(w.aside().querySelector(".fc-composer")!.hidden, true, "the composer closed all the same");
  assert.ok(w.card(twinA.id) && w.card(twinB.id), "both cards are rendered");
  w.close();
});

// ── at source ──────────────────────────────────────────────────────────────────────────────────────

test("at source: the scroll that shows a card's end is track content (no header term); the save sets the focus and raises the line BEFORE the composer closes, and scrolls nothing (decision 43); the line's click reaches a loose card through both scrollers", () => {
  assert.match(SRC, /const showCard = p\.top \+ p\.height \+ CARD_GAP - track\.clientHeight;/, "the least scroll that shows the card's bottom, in the track's content");
  assert.doesNotMatch(SRC, /const showCard = [^;\n]*offset[^;\n]*;/, "no header term in it");
  assert.match(SRC, /const lined = r !== null && this\.landSaved\(c, had, r, note\);[^\n]*\n\s*if \(r\) this\.closeComposer\(\);/, "the landing, then the close");
  assert.match(SRC, /const saved = c\.kind === "reply" \? c\.commentId : savedCommentId\(had, r, note\);\n\s*if \(saved === null\) return false;\n\s*const key = this\.cardKey\(saved\);\n\s*if \(this\.margin\) this\.focusOn\(key\);\n\s*const side = this\.cardWhere\(key\);/, "a reply's card by its comment, a new comment's off the reply's store; the focus and the card's side, never a scroll (decision 43, 2026-09-09)");
  assert.doesNotMatch(SRC.slice(SRC.indexOf("private landSaved("), SRC.indexOf("private cardWhere(")), /scrollCard|scrollBoth|scrollIntoView|centerOn|showLoose/, "nothing in the landing scrolls");
  assert.match(SRC, /if \(this\.margin && this\.focusOn\(id\) && \(this\.centerOn\(id\) \|\| this\.showLoose\(id\)\)\) return;/, "a loose card is scrolled to by both scrollers at once, never by scrollIntoView alone (the card the focus first: the focus follow-on, 2026-09-08) — the line's click comes through here");
  assert.match(SRC, /const had = new Set\(\(this\.status && this\.status\.store \? this\.status\.store\.comments : \[\]\)\.map\(\(x\) => x\.id\)\);/, "the baseline is the status the write is fenced on");
});

// ── the projection: a node's edges are own, non-enumerable properties (ui/test-dom-shim.ts), so a failing
// assertion's dump of a node stops at the node instead of walking the tree ────────────────────────────
test("a node of the stand-in enumerates its primitives alone, and its dump names neither its parent nor its children", () => {
  const root = new El("div"), row = root.appendChild(new El("p")), text = row.appendChild(new Txt("alpha"));
  row.appendChild(new El("span")).setAttribute("data-id", "x");
  for (const n of [root, row, text] as any[]) {
    assert.ok(Object.keys(n).every((k) => staysEnumerable(n[k])), "every enumerable own property is a primitive: " + Object.keys(n).join(", "));
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "the dump stops at the node");
  }
});
