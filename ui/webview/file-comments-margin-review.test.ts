// The margin layout after its review (plans/file-review.md, "The margin-layout follow-on (2026-09-07)"): the real
// panel over a DOM stand-in that models what the review's findings turned on and file-comments-margin.test.ts's
// stand-in did not — the browser's focus-fixup rule (a node taken out of the document drops the keyboard to the
// body, so a focused Accept all moved from the list to the footer lost it), scroll positions clamped to each
// scroller's range (a write the other scroller clamps raises no echo), a FOOTER under the track (Accept all ·
// Reject all, Send, the Log), so the track's box is shorter than the body's by the header and the footer both,
// a body whose content can reflow without its box changing (a <details> opened), escaped attribute selectors (a
// sidecar id holding a quote), and media bodies (a standalone image, a PDF's pages) whose region rectangles are
// the marks. The pure rule is card-layout.test.ts; the numbers a real engine measures are the browser legs.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";
import { CARD_GAP } from "./card-layout";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

// ── a DOM stand-in: ancestry, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  constructor(public type: string, init: { key?: string } = {}) { this.key = init.key || ""; }
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
const ROW = 60, OFFSET = 60, FOOTER = 40, CARD = 40, OPEN = 120, BODY_VIEW = 200, TRACK = BODY_VIEW - OFFSET - FOOTER;
const BOX = 30;                                                 // a reply's box inside an open card: the card's last BOX px, above its buttons (placeComposer)
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
    if (el.classList.contains("fc-card")) return R(412, 0, 316, el.classList.contains("open") ? OPEN : CARD);
    if (el.classList.contains("fc-hl") || el.classList.contains("fc-ins") || el.classList.contains("fc-del")) {
      const row = el.closest(".fv-cl");
      const i = row ? w.code.querySelectorAll(".fv-cl").indexOf(row) : -1;
      return i < 0 ? ZERO : R(20, 100 + ROW * i - body.scrollTop + (i >= w.reflowAt ? w.reflowBy : 0), 50, 20);
    }
    if (el.classList.contains("fc-imgwrap")) { const img = el.childNodes.find((c) => c instanceof El && c.tagName === "IMG") as El | undefined; return img ? img.getBoundingClientRect() : ZERO; }
    if (el.classList.contains("fc-overlay")) return el.parentNode ? el.parentNode.getBoundingClientRect() : ZERO;   // inset 0 in its wrap or its page's shell
    if (el.classList.contains("fc-region")) return el.parentNode ? regionBox(el, el.parentNode.getBoundingClientRect()) : ZERO;
    if (el.classList.contains("fc-composer")) {   // the reply's box in its card: the card's placed top in the viewport, plus the card's height less the box's
      const card = el.closest(".fc-card");
      if (card) return R(412, 100 + OFFSET + (parseFloat((card.style.top as string) || "0") || 0) - w.track().scrollTop + OPEN - BOX, 316, BOX);
    }
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

// ── the keyboard through the moves ─────────────────────────────────────────────────────────────────

test("Reject all in the footer keeps the keyboard through its confirm's render, and Accept all through an unrelated render: the pass moves the foot after refocus, and gives the moved control its focus back", async (t) => {
  const { w } = await open(t, textWorld());
  const send = w.send();
  const none = actIn(send, "fcrejectall")!;
  none.focus(); assert.equal(doc.activeElement, none, "Tab reached Reject all, in the footer");
  none.click(); await tick();
  const again = actIn(send, "fcrejectall")!;
  assert.ok(actIn(send, "fcrejectallgo") && actIn(send, "fcrejectallcancel"), "the confirm row is up, in the footer");
  assert.notEqual(again, none, "the render rebuilt the foot");
  assert.equal(doc.activeElement, again, "the keyboard is on the new Reject all — not on the body, which is where a moved focused node lands");
  assert.equal(w.list().querySelector(".fc-foot"), null, "the foot is not in the list");
  // an unrelated render while Accept all holds the keyboard: a card's head toggles
  const all = actIn(send, "fcacceptall")!;
  all.focus(); assert.equal(doc.activeElement, all);
  headOf(w, replied.id).click(); await tick();
  assert.ok(w.card(replied.id)!.classList.contains("open"), "the card opened");
  assert.equal(doc.activeElement, actIn(w.send(), "fcacceptall"), "Accept all still holds the keyboard after the render moved the foot again");
  w.close();
});

test("Accept all's keyboard in the margin layout: the busy render parks it on the last change card's head (the foot stands in the footer, not in the list), the reply that removes the change cards leaves it on the card now at that place", async (t) => {
  const { w, ok } = await open(t, textWorld());
  const all = actIn(w.send(), "fcacceptall")!;
  all.focus(); all.click(); await tick();
  assert.equal(actIn(w.send(), "fcacceptall")!.disabled, true, "busy: Accepting…");
  assert.ok(w.aside().contains(doc.activeElement), "the keyboard did not fall to the body");
  assert.equal(doc.activeElement, headOf(w, "chg:h1"), "it waits on the change card's head");
  // the reply: no change left; the comment card placed after the change card takes the keyboard
  await ok(status({ hunks: [], storeMtimeNs: "1757145600000000005", unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 0, watermark: null } }));
  assert.equal(w.card("chg:h1"), null, "the change card is gone");
  assert.ok(w.aside().contains(doc.activeElement), "after the reply the keyboard is still in the panel");
  assert.equal(doc.activeElement, headOf(w, closing.id), "the card now at the change card's place in the margin's order (the closing line's, placed after it) holds it");
  w.close();
});

// ── the rows stand in the footer ───────────────────────────────────────────────────────────────────

test("the list's rows stand in the footer above Send — the foot first, then the rows in the list's order: the '… N more changes' fold (its hidden changes' marks are painted, so the row saying why must be in view), the Resolved fold, and a wait's loader", async (t) => {
  const hunks = [9, 11, 13, 15, 17].map((i, n) => lineHunk(n + 1, i));   // five paragraphs: two groups fold behind the row
  const done: StoreComment = { ...replied, id: (T0 - 70000) + "-3", resolved: true };
  const s = status({ hunks, store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, passage, done] } });
  const { w, ok } = await open(t, textWorld(), s);
  const list = w.list(), send = w.send();
  assert.deepEqual(w.cardIds().filter((k) => k.startsWith("chg:")), ["chg:h1", "chg:h2", "chg:h3"], "three groups' cards are rendered");
  for (const id of ["h4", "h5"]) assert.ok(w.body.querySelectorAll(".fc-ins").some((m) => m.dataset.id === id), id + "'s mark is painted in the body though its card is folded");
  assert.equal(actIn(list, "fcmore"), null, "the fold row is not a loose item at the top of the track");
  assert.equal(actIn(list, "fcresolved"), null);
  const kinds = send.childNodes.filter((n): n is El => n instanceof El).map((n) => n.dataset.act || n.className);
  assert.deepEqual(kinds, ["fc-foot", "fcmore", "fcresolved", "fc-send"], "the foot under the footer's rule, then the fold and the Resolved fold in the list's order, then Send");
  assert.equal(actIn(send, "fcmore")!.textContent, "… 2 more changes");
  // the row does what it says, from the footer: every change card renders, level with its mark
  actIn(send, "fcmore")!.click(); await tick();
  assert.equal(w.top("chg:h5"), desired(17), "the fifth change's card is beside its mark");
  assert.equal(actIn(w.send(), "fcmore")!.textContent, "▾ Fewer changes");
  // a wait: Accept on a change whose reply moves the file — the bytes' loader stands in the footer, not out of view at the top of the track
  w.body.scrollTop = 600; w.body.dispatchEvent(new Ev("scroll"));
  actIn(w.card("chg:h1")!, "fcaccept")!.click(); await tick();
  await ok(status({ hunks: hunks.slice(1), fileMtimeNs: "1757145600000000009", storeMtimeNs: "1757145600000000010", store: s.store, unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 0, watermark: null } }));
  const load = w.send().querySelectorAll(".fc-load").find((n) => n.dataset.slot === "bytes");
  assert.ok(load, "the reload's loader is in the footer");
  assert.equal(w.list().querySelectorAll(".fc-load").length, 0, "and not in the track");
  assert.equal(w.body.scrollTop, 600, "nothing scrolled the text to show it");
  // the bytes land: the loader goes
  w.viewMtime = "1757145600000000009"; w.repaint(); await tick();
  assert.equal(w.send().querySelectorAll(".fc-load").length, 0);
  w.close();
});

// ── the order the eye reads ────────────────────────────────────────────────────────────────────────

test("the cards' DOM order is the placement's — the loose group, then by mark — so the Tab order reads down the margin; a focused head survives the reorder", async (t) => {
  const { w } = await open(t, textWorld());
  assert.deepEqual(w.cardIds(), [whole.id, detached.id, replied.id, passage.id, "chg:h1", closing.id], "not the model's order (the change card first, then comments by time)");
  const head = headOf(w, "chg:h1");
  head.focus(); assert.equal(doc.activeElement, head);
  headOf(w, replied.id).click(); await tick();          // a render: the fresh list is in the model's order until the pass re-sorts it
  assert.deepEqual(w.cardIds(), [whole.id, detached.id, replied.id, passage.id, "chg:h1", closing.id], "re-sorted after the render");
  assert.equal(doc.activeElement, headOf(w, "chg:h1"), "the keyboard is on the change card's fresh head, though the pass moved it");
  w.close();
});

// ── the far end: the footer under the track ─────────────────────────────────────────────────────────

test("the body's end is padded by the footer's height, so the two scrollers share one range and a card level with the last line sits in the track's box at the body's end — from either scroller, and from the card's reference", async (t) => {
  const { w } = await open(t, textWorld());
  const body = w.body, track = w.track(), list = w.list();
  assert.equal(body.style.paddingBottom, FOOTER + "px", "the footer's height, at the body's end");
  assert.equal(list.style.height, (CONTENT + FOOTER - BODY_VIEW + TRACK) + "px", "the list's content: the body's less the body's box plus the track's");
  const bodyMax = body.scrollHeight - body.clientHeight, trackMax = track.scrollHeight - track.clientHeight;
  assert.equal(trackMax, bodyMax, "one range: " + trackMax + " vs " + bodyMax);
  assert.equal(w.top(closing.id), desired(33));
  // the body to its end: the track comes to the same end, and the last line's card is in the track's box, level with its mark
  body.scrollTop = 1e6; body.dispatchEvent(new Ev("scroll"));
  assert.equal(body.scrollTop, bodyMax); assert.equal(track.scrollTop, bodyMax);
  const box = cardBox(w, closing.id);
  assert.ok(box.top >= TRACK_BOX.top && box.bottom <= TRACK_BOX.bottom, "the card is in the track's box, above the footer: " + JSON.stringify(box) + " in " + JSON.stringify(TRACK_BOX));
  const mark = w.body.querySelectorAll(".fc-hl").find((m) => m.dataset.id === closing.id)!.getBoundingClientRect();
  assert.equal(box.top, mark.top, "and level with its mark");
  // the reverse: the track run to its end brings the body to the same place
  body.scrollTop = 0; body.dispatchEvent(new Ev("scroll")); track.dispatchEvent(new Ev("scroll"));
  assert.equal(track.scrollTop, 0);
  track.scrollTop = 1e6; track.dispatchEvent(new Ev("scroll"));
  assert.equal(track.scrollTop, trackMax); assert.equal(body.scrollTop, bodyMax, "the body followed to its end, which is the track's");
  // the card's reference: the centering clamps at the body's end, with the card in view
  body.scrollTop = 0; body.dispatchEvent(new Ev("scroll"));
  actIn(w.card(closing.id)!, "fcgoto")!.click();
  assert.equal(body.scrollTop, bodyMax); assert.equal(track.scrollTop, bodyMax, "the track came along, not past");
  w.close();
});

test("a card hanging past the content's end grows the padding by its overhang: the body reaches the card's end itself, and a pass leaves the position", async (t) => {
  const { w } = await open(t, textWorld());
  const body = w.body, track = w.track();
  headOf(w, closing.id).click(); await tick();          // the last line's card opens: OPEN tall, its end past the content's end
  const hang = desired(33) + OPEN + 8 + OFFSET - CONTENT;   // how far the card's bottom plus the gap reaches past the content
  assert.ok(hang > 0, "the fixture hangs: " + hang);
  assert.equal(body.style.paddingBottom, (FOOTER + hang) + "px", "the footer's height plus the overhang");
  const bodyMax = body.scrollHeight - body.clientHeight;
  assert.equal(track.scrollHeight - track.clientHeight, bodyMax, "still one range");
  assert.equal(body.scrollTop, bodyMax, "the click's centering ran the body to its end");
  assert.equal(track.scrollTop, bodyMax);
  const box = cardBox(w, closing.id);
  assert.ok(box.bottom <= TRACK_BOX.bottom, "the open card's end is in the track's box: " + box.bottom + " vs " + TRACK_BOX.bottom);
  resize(); flush();                                    // a pass from an observer: the position stands
  assert.equal(track.scrollTop, bodyMax); assert.equal(body.scrollTop, bodyMax);
  // folded, the overhang goes with it: the padding is the footer's again and the ranges shrink together
  headOf(w, closing.id).click(); await tick();
  assert.equal(body.style.paddingBottom, FOOTER + "px");
  assert.equal(track.scrollTop, body.scrollTop, "the two agree after the shrink");
  w.close();
});

test("a body that does not scroll (a short file): the track goes on alone to show a card's end, a pass leaves it there, and the body's own scroll brings the track back level", async (t) => {
  // two rows: 120px of content under a 200px box, and the footer's padding leaves it short of scrolling
  const short = "# Report\nWe recommend " + QUOTE + ".\n";
  const { w } = await open(t, textWorld(short), status({ hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] } }));
  const body = w.body, track = w.track();
  assert.equal(body.scrollHeight - body.clientHeight, 0, "the body cannot scroll");
  const top = 8;                                        // row 1's mark is under the header: the layout clamps the card to the track's inset
  assert.equal(w.top(passage.id), top);
  headOf(w, passage.id).click(); await tick();          // OPEN tall from 8: its end at 128, past the track's 100px box
  assert.equal(body.scrollTop, 0, "the body could not move");
  const need = top + OPEN + 8 - TRACK;                  // the least track scroll that shows the card's end
  assert.equal(track.scrollTop, need, "the track went on alone, as far as the card's end");
  assert.ok(cardBox(w, passage.id).bottom <= TRACK_BOX.bottom, "the card's end is in the track's box");
  track.dispatchEvent(new Ev("scroll"));                // the echo of the write that moved the track (the body's write moved nothing: no echo)
  resize(); flush();                                    // a pass (a status reply's render would do the same): the track is not pulled back
  assert.equal(track.scrollTop, need, "the pass left the track where the card's end shows");
  // the person wheels the track back: the body cannot follow, and the cards are level again
  track.scrollTop = 0; track.dispatchEvent(new Ev("scroll"));
  assert.equal(track.scrollTop, 0); assert.equal(body.scrollTop, 0);
  w.close();
});

test("a write the other scroller clamps raises no echo, so the lock forgets it at once: the next genuine scroll of that scroller is mirrored, not swallowed", async (t) => {
  const { w } = await open(t, textWorld());
  const body = w.body, track = w.track();
  // the body's content grows before the pass has seen it (the observer's frame is still to come): until then the body's
  // range runs past the track's, and a body scroll near the end writes onto a track that is already at its end
  w.reflowBy = 300;
  const trackMax = track.scrollHeight - track.clientHeight;
  assert.ok(body.scrollHeight - body.clientHeight > trackMax + 200, "the body can go further than the track for now");
  body.scrollTop = trackMax + 20; body.dispatchEvent(new Ev("scroll"));
  assert.equal(track.scrollTop, trackMax, "the track followed as far as it could");
  track.dispatchEvent(new Ev("scroll"));                // the echo of a write that moved it
  body.scrollTop = trackMax + 120; body.dispatchEvent(new Ev("scroll"));   // further: the write onto the track changes nothing, and no echo will come
  assert.equal(track.scrollTop, trackMax);
  // the person wheels the cards back: a genuine track event, mirrored — not taken for an echo the last write never raised
  track.scrollTop = trackMax - 200; track.dispatchEvent(new Ev("scroll"));
  assert.equal(body.scrollTop, trackMax - 200, "the body followed the track's genuine scroll");
  w.close();
});

// ── what re-runs the pass ──────────────────────────────────────────────────────────────────────────

test("the body's content is observed, not only its box: a reflow inside it (a block above the marks opened) re-runs the pass, and the cards below move with their marks", async (t) => {
  const { w } = await open(t, textWorld());
  const wrap = w.body.querySelector(".fileview-code")!;
  assert.ok(watched().has(wrap), "the body's content root is held by the size observer");
  assert.ok(watched().has(w.body) && watched().has(w.main) && watched().has(w.track()), "the body, the row and the track too");
  assert.equal(w.top(replied.id), desired(3)); assert.equal(w.top(passage.id), desired(5));
  w.reflowAt = 4; w.reflowBy = 100;                     // rows from 4 on sit 100px lower: the body's box is unchanged, its content is taller
  resized(wrap);
  assert.equal(w.top(replied.id), desired(3), "row 3 did not move");
  assert.equal(w.top(passage.id), desired(5) + 100, "row 5's card followed its mark down");
  assert.equal(w.top("chg:h1"), desired(7) + 100);
  assert.equal(w.list().style.height, (CONTENT + 100 + FOOTER - BODY_VIEW + TRACK) + "px", "the track's content grew with the body's");
  w.close();
});

test("cards the list layout held are observed when the margin layout comes on outside a render, so a card growing without a render pushes the ones below", async (t) => {
  const { w } = await open(t, textWorld());
  narrow = true; resize(); flush();
  assert.ok(!w.aside().classList.contains("fc-margin"), "the list layout");
  assert.ok(!watched().has(w.card(replied.id)!), "no card is observed in the list layout");
  narrow = false; resize(); flush();
  assert.ok(w.aside().classList.contains("fc-margin"), "the margin layout is back, without a render");
  const card = w.card(replied.id)!;
  assert.ok(watched().has(card), "the cards the list held are observed now");
  assert.equal(w.top(passage.id), desired(5));
  card.classList.add("open");                           // grown without a render (a web font arriving, say): the card observer alone sees it
  resized(card);
  assert.equal(w.top(passage.id), desired(3) + OPEN + 8, "the card below moved down");
  w.close();
});

// ── a sidecar id the selector must quote ──────────────────────────────────────────────────────────

test("a comment id holding a quote: the pass builds its selectors escaped, so the render places every card instead of throwing", async (t) => {
  const odd: StoreComment = { ...replied, id: 'x"]' };
  const { w } = await open(t, textWorld(), status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, odd, passage] } }));
  assert.equal(w.top(odd.id), desired(3), "the odd id's card is level with its mark");
  assert.equal(w.top(passage.id), desired(5), "and so is the next one");
  assert.ok(w.list().style.height, "the list has its height: the pass ran to its end");
  actIn(w.card(odd.id)!, "fcgoto")!.click();            // its reference: the same selector
  assert.ok(w.body.scrollTop >= 0);
  w.close();
});

// ── the layout ends with the panel ─────────────────────────────────────────────────────────────────

test("closing the panel takes the body's end padding and the margin class with it; reopening brings both back", async (t) => {
  const { w, button, ok } = await open(t, textWorld());
  assert.equal(w.body.style.paddingBottom, FOOTER + "px");
  const aside = w.aside();
  button.click();                                       // close
  assert.equal(w.body.style.paddingBottom, "", "the body is the viewer's again");
  assert.ok(!aside.classList.contains("fc-margin"));
  button.click(); await ok();                           // reopen
  assert.ok(w.aside().classList.contains("fc-margin"));
  assert.equal(w.body.style.paddingBottom, FOOTER + "px");
  assert.equal(w.top(replied.id), desired(3));
  w.close();
});

// ── media: the region rectangles are the marks ────────────────────────────────────────────────────

test("a standalone image: the region's card sits level with its rectangle, and the picture's load re-measures it", async (t) => {
  const w = imageWorld();
  await open(t, w, mediaStatus("figure.png", [imageComment]));
  assert.ok(w.aside().classList.contains("fc-margin"), "the margin layout over a media body");
  const rect = w.body.querySelectorAll(".fc-region").find((r) => r.dataset.id === RID)!;
  assert.ok(rect, "the rectangle is painted");
  const top = rect.getBoundingClientRect().top;
  assert.equal(top, IMG_RECT.top + REGION.y * IMG_RECT.height, "the stand-in places the rectangle by its percentages");
  assert.equal(w.top(RID), top - 100 - OFFSET, "the card's top is the rectangle's, in the track's content");
  assert.equal(w.card(RID)!.dataset.pushed, undefined);
  // the picture loads taller: its rectangle moves, and the load (captured on the body) re-runs the pass
  w.img.rect = R(100, 260, 300, 200);
  frames.length = 0;
  w.img.dispatchEvent(new Ev("load"));
  assert.equal(frames.length, 1, "one pass scheduled");
  flush();
  assert.equal(w.top(RID), 260 + REGION.y * 200 - 100 - OFFSET, "the card followed the rectangle");
  w.close();
});

test("a PDF: a region on a page with a box is placed beside its rectangle on the first pass, undrawn; a page with no box yet leaves its card loose, and the draw's repaint places it", async (t) => {
  const w = pdfWorld(PAGE_RECTS);
  await open(t, w, mediaStatus("deck.pdf", [pageComment]));
  const p2 = PAGE_RECTS[1];
  assert.ok(w.pages[1].querySelectorAll(".fc-region").some((r) => r.dataset.id === RID), "the rectangle is on page 2's overlay");
  assert.equal(w.top(RID), p2.top + REGION.y * p2.height - 100 - OFFSET, "the card is level with the rectangle: " + w.top(RID));
  assert.ok(IO.all.some((io) => io.targets.has(w.pages[0])) && !IO.all.some((io) => io.targets.has(w.pages[1])), "page 1 (no rectangle) waits for the reader; page 2 took its overlay at once");
  w.close();
  // the same, with page 2's shell measuring nothing yet
  const w2 = pdfWorld([PAGE_RECTS[0], null]);
  await open(t, w2, mediaStatus("deck.pdf", [pageComment]));
  assert.equal(w2.top(RID), 8, "no box: the loose group, at the top of the track");
  w2.pages[1].rect = p2; w2.canvases[1].rect = p2;       // the page draws: the chunk's onPage fires the seam's onRendered
  w2.repaint(); await tick();
  assert.equal(w2.top(RID), p2.top + REGION.y * p2.height - 100 - OFFSET, "placed beside its rectangle by the draw's repaint");
  w2.close();
});

// ── at source ──────────────────────────────────────────────────────────────────────────────────────

test("at source: the id selectors are escaped; the moves that can detach a focused control run through the one helper that gives the focus back; the body's content joins the observer per pass", () => {
  assert.match(SRC, /function cssId\(s: string\): string \{/, "one escape helper for the panel: the composer follow-on's cssId");
  assert.match(SRC, /querySelectorAll\('\[data-act="' \+ act \+ '"\]\[data-id="' \+ cssId\(id\) \+ '"\]'\)/, "ownMarks");
  assert.match(SRC, /'\.fc-card\[data-id="' \+ cssId\(k\.card\) \+ '"\]'/, "focusNear");
  assert.match(SRC, /private moving\(nodes: HTMLElement\[\], move: \(\) => void\): void \{\n\s*const held = document\.activeElement/);
  assert.match(SRC, /this\.moving\(rows, \(\) => \{\n\s*if \(foot\) this\.sections\.send\.insertBefore\(foot, this\.sections\.send\.firstChild\);\n\s*for \(const r of rows\) if \(r !== foot\) send\.insertBefore\(r, box\);/, "the rows' move: the foot first, the others in the list's order");
  assert.match(SRC, /this\.moving\(order, \(\) => \{ for \(const node of order\) list\.appendChild\(node\); \}\);/, "the reorder");
  assert.match(SRC, /private watchContent\(body: HTMLElement\): void/);
  assert.match(SRC, /this\.watchContent\(body\);\n\s*const kids = /, "each pass, before the cards are read");
  assert.match(SRC, /private padBody\(body: HTMLElement, px: number\): void/);
  assert.match(SRC, /if \(this\.margin\) this\.layoutOff\(\);\s*\/\/ the body's end padding/, "closePanel ends the layout");
});

// ── the reply's box in its card (the composer follow-on, merged 2026-09-08) ─────────────────────────

test("a reply's box stands inside its card in the track: the pass leaves it there (no row of the footer's, no child of the list the sheet positions), and Reply brings it into the track's box through both scrollers, after the pass, not by a track-only scrollIntoView", async (t) => {
  const { w } = await open(t, textWorld());
  const body = w.body, track = w.track();
  headOf(w, closing.id).click(); await tick();           // the last line's card opens (its Reply is in the open card) and its mark is centered
  body.scrollTop = 0; body.dispatchEvent(new Ev("scroll"));   // back to the top of the text: the card, at row 33, is far below the track's box
  assert.equal(track.scrollTop, 0);
  scrolledInto.length = 0;
  actIn(w.card(closing.id)!, "fcreply")!.click(); await tick();
  const card = w.card(closing.id)!, box = w.aside().querySelector(".fc-composer")!;
  assert.ok(card.contains(box), "the box stands in the card (placeComposer)");
  assert.notEqual(box.parentNode, w.list(), "a descendant of the card, not a child of the list: the sheet's absolute positioning does not reach it");
  assert.ok(!w.send().contains(box), "and not a row moveRows takes to the footer");
  assert.ok(card.classList.contains("open") && w.top(closing.id) === desired(33), "the card is open and placed at its mark");
  // the box's bottom plus the gap into the track's box, by the least scroll — the body's position too (scrollBoth)
  const want = desired(33) + OPEN + CARD_GAP - TRACK;
  assert.equal(track.scrollTop, want, "the track shows the box's end");
  assert.equal(body.scrollTop, want, "the body came along: one range, so the next pass has nothing to pull back");
  assert.equal(scrolledInto.length, 0, "no scrollIntoView: the track alone would be pulled back to the body by the next pass");
  resize(); flush();                                     // a pass leaves the position
  assert.equal(track.scrollTop, want); assert.equal(body.scrollTop, want);
  // the words survive the poll's re-render around the box (swapCards), and the box's card keeps its place
  const input = box.querySelector("textarea")!;
  input.value = "Agreed"; w.repaint(); await tick();
  assert.equal(w.aside().querySelector(".fc-composer")!, box, "the same node");
  assert.equal(input.value, "Agreed");
  assert.ok(w.card(closing.id)!.contains(box) && w.top(closing.id) === desired(33));
  w.close();
});

test("at source: the box's scroll runs after the margin pass and through showComposer; outside the margin layout showComposer is scrollIntoView's nearest", () => {
  assert.match(SRC, /const moved = typing && this\.composerBox\.parentElement !== home;\n(?:[^\n]*\n)*?\s*this\.afterRender\(\);[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*if \(keep\) this\.refocus\(keep, want, true\);\n\s*if \(moved\) this\.showComposer\(\);/, "render: after the pass");
  assert.match(SRC, /this\.render\(\);\n\s*this\.showComposer\(\);/, "startReply");
  assert.doesNotMatch(SRC, /this\.composerBox\.scrollIntoView/, "never the track alone");
  assert.match(SRC, /private showComposer\(\): void \{\n\s*const box = this\.composerBox, track = this\.sections\.cards;\n\s*if \(!this\.margin \|\| !track\.contains\(box\)\) \{ box\.scrollIntoView\(\{ block: "nearest" \}\); return; \}/, "the list layout, and the slot above the track, as before");
  assert.match(SRC, /else if \(top \+ r\.height \+ CARD_GAP > at \+ view\) want = top \+ r\.height \+ CARD_GAP - view;\n\s*this\.scrollBoth\(want\);/, "the least scroll that shows the box, onto both scrollers");
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
