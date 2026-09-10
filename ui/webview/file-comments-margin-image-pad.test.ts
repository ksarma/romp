// The body's end padding over a body that does not scroll (plans/file-review.md, "The margin-layout follow-on
// (2026-09-07)", its third review round): the pass pads the body by the footer's height so the body can scroll a card
// in the text's last lines into the track's box — and a box's padding comes out of its content box. Content sized to
// the box by a `min-height: 100%` (the standalone picture's box, .fileview-imgbox, which centers the picture in itself;
// the Raw view's .fileview-code) shrank by the padding instead of scrolling: the body gained no range, and the centered
// picture rose by half the footer at every open of the panel and fell back at the close, a layout shift on no new
// information about the picture. The pass now writes the padding, measures, and takes it back the same pass where it
// bought no range; where it did (a picture nearly the box's height, whose own box outgrows the padded content box) it
// stays, as the padding that lets the body reach a card at the picture's foot. The stand-in is
// file-comments-margin-review.test.ts's (clamped scroll positions, a footer under the track), with a picture world that
// models the box's min-height and the centering: the picture's top is where the box's height puts it, and the box is
// the body's content box or the picture's own height, whichever is more. The numbers a real engine measures are
// file-comments-margin-image-browser.test.ts. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
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
const ROOT = "/repo/notes-api";
const ABS = ROOT + "/docs/report.md";
const PNG = ROOT + "/docs/figure.png";
const T0 = 1757145600000;
const QUOTE = "shipping the cache in v1.2";
const H1 = "1111111111111111111111111111111111111111111111111111111111111111";
const REGION = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 };
const RID = T0 + "-0";
const imageComment: StoreComment = { id: RID, author: "you", ts: T0, body: "Crop the header.", replies: [], resolved: false, target: { kind: "image", region: REGION, hash: H1 } as StoreComment["target"] };
const passage: StoreComment = {   // row 1 of the short report
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: QUOTE, prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
// the short report: two rows of text under a box taller than both, so the body cannot scroll; the long one scrolls
const SHORT = "# Report\nWe recommend " + QUOTE + ".\n";
const LONG = "# Report\n\n## Findings\n" + Array.from({ length: 30 }, (_, i) => "Line " + i + " of the report.").join("\n") + "\nWe recommend " + QUOTE + ".\n";
function mediaStatus(comments: StoreComment[]): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Ffigure.png.json", trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: null,
    store: { v: 3, path: "docs/figure.png", suggestions: [], comments }, hunks: [], log: [],
    unsent: { comments: comments.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
    fileHash: H1,
  };
}
function textStatus(): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] }, hunks: [], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
  };
}

// ── the viewer stand-in: the body row, the seam as closures, a measurement table ───────────────────
// Geometry: the body's box is at viewport y=100, BODY_VIEW tall; the header stands OFFSET tall above the track and the
// footer FOOTER tall below it, so the track's box is TRACK tall; a card is CARD tall. The picture's box (.fileview-imgbox)
// pads the picture by IMG_PAD on each side and is as tall as the body's CONTENT box (the box less the padding the pass
// writes) or as its own content, whichever is more — the sheet's `min-height: 100%` — and centers the picture in itself.
// The Raw view's rows sit at 100 + ROW·i − scrollTop; its box has the same min-height and stacks from the top.
const ROW = 60, OFFSET = 60, FOOTER = 40, CARD = 40, OPEN = 120, BODY_VIEW = 200, TRACK = BODY_VIEW - OFFSET - FOOTER, IMG_PAD = 14;
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  editing: boolean; viewMtime: string;
  content: number;                                             // the body's own content height, padding aside (the Raw view's rows; the picture's box at its own height)
  pad(): number; boxHeight(): number;
  measure(el: El): Rect; scrollHeightOf(el: El): number; clientHeightOf(el: El): number;
  repaint(): void; close(): void;
  aside(): El; track(): El; list(): El; card(key: string): El | null; top(key: string): number | null;
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
    viewMtime: "1757145600000000001", content,
  } as World;
  w.pad = () => parseFloat((body.style.paddingBottom as string) || "0") || 0;
  w.boxHeight = () => Math.max(BODY_VIEW - w.pad(), w.content);          // min-height: 100% of the content box, or its own content
  w.scrollHeightOf = (el) => {
    if (el === body) return Math.max(w.boxHeight() + w.pad(), BODY_VIEW);
    if (el.classList.contains("fc-sec-cards")) { const l = el.childNodes.find((n) => n instanceof El) as El | undefined; return Math.max(l ? parseFloat((l.style.height as string) || "0") || 0 : 0, TRACK); }
    return 0;
  };
  w.clientHeightOf = (el) => (el === body ? BODY_VIEW : el.classList.contains("fc-sec-cards") ? TRACK : 0);
  w.measure = (el: El): Rect => {
    if (el === body) return R(0, 100, 400, BODY_VIEW);
    if (el.classList.contains("fc-sec-cards")) return R(400, 100 + OFFSET, 340, TRACK);
    if (el.classList.contains("fc-card")) return R(412, 0, 316, el.classList.contains("open") ? OPEN : CARD);
    if (el.classList.contains("fileview-imgbox") || el.classList.contains("fileview-code")) return R(0, 100 - body.scrollTop, 400, w.boxHeight());
    if (el.tagName === "IMG" && el.classList.contains("fileview-img")) {     // centered in its box: align-items: center
      const h = w.content - 2 * IMG_PAD;
      return R(50, 100 - body.scrollTop + (w.boxHeight() - h) / 2, 300, h);
    }
    if (el.classList.contains("fc-hl")) {
      const row = el.closest(".fv-cl");
      const i = row ? w.code.querySelectorAll(".fv-cl").indexOf(row) : -1;
      return i < 0 ? ZERO : R(20, 100 + ROW * i - body.scrollTop, 50, 20);
    }
    if (el.classList.contains("fc-imgwrap")) { const img = el.childNodes.find((c) => c instanceof El && c.tagName === "IMG") as El | undefined; return img ? img.getBoundingClientRect() : ZERO; }
    if (el.classList.contains("fc-overlay")) return el.parentNode ? el.parentNode.getBoundingClientRect() : ZERO;   // inset 0 in its wrap
    if (el.classList.contains("fc-region")) return el.parentNode ? regionBox(el, el.parentNode.getBoundingClientRect()) : ZERO;
    if (el.parentNode && el.parentNode.classList.contains("fc-cards")) return R(412, 0, 316, 20);   // a loader, a row, a fold button
    return ZERO;
  };
  w.aside = () => main.querySelector(".fileview-aside")!;
  w.track = () => w.aside().querySelector(".fc-sec-cards")!;
  w.list = () => w.track().querySelector(".fc-cards")!;
  w.card = (key) => w.aside().querySelectorAll(".fc-card").find((c) => c.dataset.id === key) || null;
  w.top = (key) => { const c = w.card(key); const t = c ? c.style.top : undefined; return typeof t === "string" ? parseFloat(t) : null; };
  w.repaint = () => { for (const cb of w.hooks.rendered) cb(); };
  w.close = () => { for (const cb of w.hooks.close.splice(0)) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const noop = () => { /* inert */ };
function ctxBase(w: World, over: Partial<FileViewActionCtx>): FileViewActionCtx {
  return {
    path: ABS, sid: SID, todoId: null,
    body: () => w.body as unknown as HTMLElement, mode: () => "raw", text: () => SHORT, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: noop, onSaved: noop, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => w.editing, setTrackedEdit: (_t: TrackedEdit | null) => { /* inert */ }, guardClose: noop,   // the viewer's close ask (main, 2026-09-07): the stand-in asks nothing
    aside: (node) => { w.main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); w.main.appendChild(n); } },
    setMode: noop, scrollToOffset: noop, reload: noop,
    ...over,
  };
}
/** The Raw view of `src`: `.fileview-code > pre > code.hljs` with a row per line, the box as tall as its rows or the body. */
function textWorld(src: string): World {
  const body = new El("div"); body.className = "fileview-body";
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre); body.appendChild(wrap);
  const w = baseWorld(body, ROW * (src.split("\n").length - 1));
  w.code = code;
  rows(code, src);
  w.ctx = ctxBase(w, { text: () => src });
  return w;
}
/** A standalone picture `imgH` tall: `.fileview-imgbox > img.fileview-img`, the box's own height the picture's plus its padding. */
function imageWorld(imgH: number): World & { img: El } {
  const body = new El("div"); body.className = "fileview-body";
  const box = new El("div"); box.className = "fileview-imgbox";
  const img = new El("img"); img.className = "fileview-img"; img.setAttribute("src", "blob:romp/figure");
  img.naturalWidth = 600; img.naturalHeight = 400; img.complete = true;
  box.appendChild(img); body.appendChild(box);
  const w = baseWorld(body, imgH + 2 * IMG_PAD) as World & { img: El };
  w.img = img; w.code = new El("code");
  w.ctx = ctxBase(w, { path: PNG, mode: () => "media", text: () => null, media: () => "image", mediaElement: () => img as unknown as HTMLElement });
  return w;
}
type Posted = Record<string, any>;
type Ctx = { after(fn: () => void): void };
async function open<W extends World>(t: Ctx, w: W, s: Status) {
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
const imgTop = (w: World & { img: El }): number => w.img.getBoundingClientRect().top;
const rectTop = (w: World): number => { const r = w.body.querySelectorAll(".fc-region").find((x) => x.dataset.id === RID); assert.ok(r, "the rectangle is painted"); return r!.getBoundingClientRect().top; };

// ── a picture shorter than the box ─────────────────────────────────────────────────────────────────

test("a picture shorter than the box: the footer's padding buys the body no scroll range, so the pass takes it back, and the picture stays where the box centered it — with its card level with the rectangle", async (t) => {
  const w = imageWorld(100);                            // a 128px box in a 200px body: centered, the picture's top is 150
  assert.equal(imgTop(w), 150, "before the panel opens");
  assert.equal(w.body.scrollHeight, w.body.clientHeight, "the body does not scroll");
  const { button } = await open(t, w, mediaStatus([imageComment]));
  assert.ok(w.aside().classList.contains("fc-margin"), "the margin layout over the media body");
  assert.equal(w.body.style.paddingBottom, "", "the padding bought no range: taken back the same pass");
  assert.equal(w.body.scrollHeight, w.body.clientHeight, "still no range");
  assert.equal(imgTop(w), 150, "the picture did not move");
  assert.equal(w.boxHeight(), BODY_VIEW, "its box is the body's whole content box");
  assert.equal(w.top(RID), rectTop(w) - 100 - OFFSET, "the card is level with the rectangle");
  // a pass from an observer (the body's, the row's): the same verdict, no flap
  resize(); flush();
  assert.equal(w.body.style.paddingBottom, "");
  assert.equal(imgTop(w), 150);
  // the panel closes: the body is the viewer's again, the picture where it was
  button.click();
  assert.equal(w.body.style.paddingBottom, "");
  assert.equal(imgTop(w), 150);
  w.close();
});

test("with no comment yet the footer holds the empty note too: the verdict is the same, the picture stays put", async (t) => {
  const w = imageWorld(100);
  await open(t, w, mediaStatus([]));
  assert.ok(w.aside().classList.contains("fc-margin"));
  assert.equal(w.body.style.paddingBottom, "");
  assert.equal(imgTop(w), 150);
  w.close();
});

// ── a picture nearly the box's height ──────────────────────────────────────────────────────────────

test("a picture nearly the box's height: the padding lengthens the body (the picture's own box outgrows the padded content box), so it stays, and the body can scroll a card at the picture's foot into the track", async (t) => {
  const w = imageWorld(160);                            // a 188px box in a 200px body: no scroll before, the picture's top at 120
  assert.equal(imgTop(w), 120);
  assert.equal(w.body.scrollHeight, w.body.clientHeight, "the body does not scroll before the panel opens");
  const { button } = await open(t, w, mediaStatus([imageComment]));
  assert.equal(w.body.style.paddingBottom, FOOTER + "px", "the footer's padding is kept: it bought range");
  const range = w.content + FOOTER - BODY_VIEW;         // 28: the box at its own height plus the padding, past the body's box
  assert.equal(w.body.scrollHeight - w.body.clientHeight, range, "the body scrolls by what the padding added");
  assert.equal(w.list().style.height, (range + TRACK) + "px", "one range: the track's content is the body's range plus its box");
  assert.equal(imgTop(w), 100 + IMG_PAD, "the picture sits at the top of its own box now (no longer centered in the body's), as the padded end asks");
  assert.equal(w.top(RID), Math.max(8, rectTop(w) - 100 - OFFSET), "the card is level with the rectangle (or at the track's inset when the mark is under the header)");
  // a pass from an observer: the body scrolls now, so the padding is the footer plus the overhang (none here) — unchanged, no flap
  resize(); flush();
  assert.equal(w.body.style.paddingBottom, FOOTER + "px");
  assert.equal(w.body.scrollHeight - w.body.clientHeight, range);
  // closing the panel: the padding goes and the picture is centered in the body's box again
  button.click();
  assert.equal(w.body.style.paddingBottom, "");
  assert.equal(imgTop(w), 120);
  w.close();
});

// ── the same rule over a text body ─────────────────────────────────────────────────────────────────

test("a short file (the Raw view's box has the same min-height): the padding bought no range and is taken back; a file that scrolls keeps the footer's padding as before", async (t) => {
  const short = textWorld(SHORT);                       // two rows, 120px, in a 200px body
  await open(t, short, textStatus());
  assert.ok(short.aside().classList.contains("fc-margin"));
  assert.equal(short.body.scrollHeight, short.body.clientHeight, "the body cannot scroll");
  assert.equal(short.body.style.paddingBottom, "", "no range bought: no padding left on the body");
  assert.equal(short.top(passage.id), 8, "row 1's mark is under the header: the card at the track's inset, as before");
  short.close();
  const long = textWorld(LONG);                         // thirty-odd rows: the body scrolls
  await open(t, long, textStatus());
  assert.ok(long.body.scrollHeight > long.body.clientHeight);
  assert.equal(long.body.style.paddingBottom, FOOTER + "px", "a body that scrolls is padded by the footer, so the two scrollers share one range");
  assert.equal(long.body.scrollHeight - long.body.clientHeight, long.content + FOOTER - BODY_VIEW);
  long.close();
});

// ── at source ──────────────────────────────────────────────────────────────────────────────────────

test("at source: the pass writes the footer's padding, then takes it back where the body gained no range", () => {
  assert.match(SRC, /const scrolls = body\.scrollHeight > body\.clientHeight;\n\s*const content = scrolls \? body\.scrollHeight - this\.bodyPad : null;/, "the body's scrolling is read before the write");
  assert.match(SRC, /this\.padBody\(body, Math\.ceil\(footer \+ hang\)\);\n\s*if \(!scrolls && body\.scrollHeight <= body\.clientHeight\) this\.padBody\(body, 0\);/, "written, measured, taken back");
  assert.match(SRC, /min-height: 100%/, "the comment names the rule the padding runs into");
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
